"""
Inference Engine - Voice authentication logic
----------------------------------------------
Uses ECAPA-TDNN with calibrated thresholds.
"""
import numpy as np
import soundfile as sf
import io
import tempfile
from pathlib import Path
from typing import Tuple, Optional
import hashlib
import logging

from app.core.model_loader import get_verifier
from app.config.settings import (
    SAMPLE_RATE, MAX_AUDIO_DURATION_SEC,
    THRESHOLD_HIGH, THRESHOLD_BORDERLINE, THRESHOLD_IMPOSTER
)

logger = logging.getLogger(__name__)


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """Normalize audio with auto-gain."""
    # Remove DC offset
    audio = audio - np.mean(audio)
    
    # Auto-gain to target RMS
    current_rms = np.sqrt(np.mean(audio**2))
    target_rms = 0.20
    
    if current_rms > 0.001:
        auto_gain = target_rms / current_rms
        auto_gain = min(auto_gain, 30.0)  # Limit gain
        audio = audio * auto_gain
    
    # Clip and normalize
    audio = np.clip(audio, -1.0, 1.0)
    max_val = np.max(np.abs(audio))
    if max_val > 0.01:
        audio = audio / max_val * 0.95
    
    return audio


def validate_audio(audio_bytes: bytes) -> Tuple[bool, str, Optional[np.ndarray]]:
    """
    Validate and preprocess audio data.
    
    Returns:
        (is_valid, error_message, audio_array)
    """
    try:
        # Read audio from bytes
        audio_io = io.BytesIO(audio_bytes)
        audio, sr = sf.read(audio_io)
        
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # Check duration
        duration = len(audio) / sr
        if duration < 1.0:
            return False, "Audio too short (min 1 second)", None
        if duration > MAX_AUDIO_DURATION_SEC:
            return False, f"Audio too long (max {MAX_AUDIO_DURATION_SEC} seconds)", None
        
        # Resample if needed
        if sr != SAMPLE_RATE:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
        
        # Normalize audio
        audio = normalize_audio(audio.astype(np.float32))
        
        return True, "", audio
        
    except Exception as e:
        return False, f"Invalid audio format: {str(e)}", None


def authenticate_voice(audio: np.ndarray, user_id: str) -> Tuple[bool, float, str]:
    """
    Authenticate voice with ECAPA-TDNN decision bands.
    
    Returns:
        (is_authenticated, confidence_score, decision)
    """
    verifier = get_verifier()
    
    # Check if user exists
    if not verifier.voiceprint_manager.user_exists(user_id):
        return False, 0.0, "USER_NOT_ENROLLED"
    
    try:
        verified, score, _ = verifier.verify_speaker(audio, user_id)
        
        # Decision bands per ECAPA-TDNN calibration
        if score >= THRESHOLD_HIGH:
            decision = "AUTHENTIC_HIGH_CONFIDENCE"
            authenticated = True
        elif score >= THRESHOLD_BORDERLINE:
            decision = "AUTHENTIC_MEDIUM_CONFIDENCE"
            authenticated = True
        elif score >= THRESHOLD_IMPOSTER:
            decision = "BORDERLINE_REVIEW_REQUIRED"
            authenticated = False
        else:
            decision = "IMPOSTER_DETECTED"
            authenticated = False
        
        logger.info(f"Auth {user_id}: score={score:.3f}, decision={decision}")
        return authenticated, max(0.0, min(1.0, score)), decision
        
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return False, 0.0, "ERROR"


def enroll_voice(audio_samples: list, user_id: str, overwrite: bool = False) -> Tuple[bool, str]:
    """
    Enroll a new user.
    
    Args:
        audio_samples: List of audio byte arrays (min 3)
        user_id: User identifier
        overwrite: Whether to overwrite existing enrollment
    
    Returns:
        (success, message)
    """
    verifier = get_verifier()
    
    # Check if exists
    if verifier.voiceprint_manager.user_exists(user_id) and not overwrite:
        return False, f"User '{user_id}' already enrolled"
    
    if len(audio_samples) < 3:
        return False, "Need at least 3 audio samples"
    
    temp_files = []
    validation_info = []
    
    try:
        # Process each sample
        for i, audio_bytes in enumerate(audio_samples):
            is_valid, error, audio = validate_audio(audio_bytes)
            size_kb = len(audio_bytes) / 1024
            
            if not is_valid:
                logger.error(f"Sample {i+1} validation failed: {error}, size: {size_kb:.1f}KB")
                return False, f"Sample {i+1}: {error}"
            
            # Log audio info
            duration = len(audio) / SAMPLE_RATE
            logger.info(f"Sample {i+1}: {size_kb:.1f}KB, {duration:.2f}s, validated OK")
            validation_info.append(f"s{i+1}:{duration:.1f}s")
            
            temp_path = tempfile.mktemp(suffix=".wav")
            sf.write(temp_path, audio, SAMPLE_RATE)
            temp_files.append(temp_path)
        
        # Enroll
        success, details = verifier.enroll_user(user_id, temp_files, overwrite=True)
        
        if success:
            return True, f"User '{user_id}' enrolled successfully with {len(temp_files)} samples"
        else:
            # Include sample_details in error for debugging
            reason = details.get("reason", "Enrollment failed")
            sample_details = details.get("sample_details", [])
            failed_samples = [s for s in sample_details if s.get("status") == "failed"]
            if failed_samples:
                reasons = [f"s{s['sample']}:{s.get('reason','unknown')}" for s in failed_samples]
                reason = f"{reason} | Failed: {', '.join(reasons)}"
            return False, reason
            
    except Exception as e:
        logger.error(f"Enrollment exception: {e}")
        return False, f"Enrollment error: {str(e)}"
            
    finally:
        # Cleanup temp files
        for f in temp_files:
            Path(f).unlink(missing_ok=True)


def get_audio_hash(audio_bytes: bytes) -> str:
    """Get SHA256 hash of audio for logging."""
    return hashlib.sha256(audio_bytes).hexdigest()[:16]
