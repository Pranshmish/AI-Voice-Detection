"""
Inference Engine - Voice authentication logic
"""
import numpy as np
import soundfile as sf
import io
import tempfile
from pathlib import Path
from typing import Tuple, Optional
import hashlib

from app.core.model_loader import get_verifier
from app.config.settings import AUDIO_BOOST, SAMPLE_RATE, MAX_AUDIO_DURATION_SEC


def boost_audio(audio: np.ndarray) -> np.ndarray:
    """Boost and normalize audio signal."""
    # Remove DC offset
    audio = audio - np.mean(audio)
    
    # Boost
    audio = audio * AUDIO_BOOST
    
    # Clip to prevent distortion
    audio = np.clip(audio, -1.0, 1.0)
    
    # Normalize
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
        
        # Boost audio
        audio = boost_audio(audio.astype(np.float32))
        
        return True, "", audio
        
    except Exception as e:
        return False, f"Invalid audio format: {str(e)}", None


def authenticate_voice(audio: np.ndarray, user_id: str) -> Tuple[bool, float, str]:
    """
    Authenticate voice against enrolled user.
    
    Returns:
        (is_authenticated, confidence_score, decision)
    """
    verifier = get_verifier()
    
    # Check if user exists
    if not verifier.voiceprint_manager.user_exists(user_id):
        return False, 0.0, "USER_NOT_ENROLLED"
    
    # Verify speaker directly from memory (no disk I/O)
    try:
        verified, score, _ = verifier.verify_speaker(audio, user_id)
        
        if verified:
            decision = "AUTHENTIC"
        elif score < 0.15:
            decision = "IMPOSTER"
        elif score < 0.30:
            decision = "IMPOSTER"
        else:
            decision = "REVIEW_REQUIRED"
        
        return verified, max(0.0, min(1.0, score)), decision
        
    except Exception as e:
        return False, 0.0, "ERROR"


def enroll_voice(audio_samples: list, user_id: str, overwrite: bool = False) -> Tuple[bool, str]:
    """
    Enroll a new user.
    
    Args:
        audio_samples: List of audio byte arrays
        user_id: User identifier
        overwrite: Whether to overwrite existing enrollment
    
    Returns:
        (success, message)
    """
    verifier = get_verifier()
    
    # Check if exists
    if verifier.voiceprint_manager.user_exists(user_id) and not overwrite:
        return False, f"User '{user_id}' already enrolled"
    
    temp_files = []
    try:
        # Process each sample
        for i, audio_bytes in enumerate(audio_samples):
            is_valid, error, audio = validate_audio(audio_bytes)
            if not is_valid:
                return False, f"Sample {i+1}: {error}"
            
            temp_path = tempfile.mktemp(suffix=".wav")
            sf.write(temp_path, audio, SAMPLE_RATE)
            temp_files.append(temp_path)
        
        # Enroll
        success, details = verifier.enroll_user(user_id, temp_files, overwrite=True)
        
        if success:
            return True, f"User '{user_id}' enrolled successfully"
        else:
            return False, details.get("reason", "Enrollment failed")
            
    finally:
        # Cleanup temp files
        for f in temp_files:
            Path(f).unlink(missing_ok=True)


def get_audio_hash(audio_bytes: bytes) -> str:
    """Get SHA256 hash of audio for logging (no raw audio stored)."""
    return hashlib.sha256(audio_bytes).hexdigest()[:16]
