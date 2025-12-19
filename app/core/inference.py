"""
Voice Authentication Inference Module
Core functions for voice authentication and enrollment
"""
import logging
import numpy as np
import io
import soundfile as sf
from typing import Optional, List, Tuple, Union

logger = logging.getLogger(__name__)

def validate_audio(audio_bytes: bytes) -> Tuple[bool, str, Optional[np.ndarray]]:
    """
    Validate and normalize audio data.
    Supports WAV, MP3, WebM, OGG formats.
    Returns: (is_valid, message, audio_array)
    """
    logger.info(f"Validating audio: {len(audio_bytes)} bytes")
    
    # Try soundfile first (fastest for WAV)
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio, sr = sf.read(audio_file)
        logger.info(f"Soundfile loaded: sr={sr}, shape={audio.shape}")
    except Exception as e:
        logger.warning(f"Soundfile failed, trying pydub: {e}")
        
        # Fallback to pydub for WebM/OGG/MP3
        try:
            from pydub import AudioSegment
            
            audio_file = io.BytesIO(audio_bytes)
            # Try to detect format
            audio_segment = AudioSegment.from_file(audio_file)
            
            # Convert to mono 16kHz
            audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)
            
            # Get raw samples as numpy array
            samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32)
            samples = samples / 32768.0  # Convert from int16 to float
            
            audio = samples
            sr = 16000
            logger.info(f"Pydub loaded: sr={sr}, samples={len(audio)}")
        except Exception as e2:
            logger.error(f"Both soundfile and pydub failed: {e2}")
            return False, f"Invalid audio format: {str(e)}", None
    
    # Convert stereo to mono
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
    
    # Check duration
    duration = len(audio) / sr
    logger.info(f"Audio duration: {duration:.2f}s")
    
    if duration < 0.5:
        return False, f"Audio too short: {duration:.2f}s (need >= 0.5s)", None
    if duration > 30:
        return False, f"Audio too long: {duration:.2f}s (max 30s)", None
    
    # Normalize audio
    max_val = np.max(np.abs(audio))
    if max_val > 1e-6:  # Avoid division by zero
        audio = audio / max_val
    else:
        logger.warning("Audio is silent or near-silent")
    
    return True, "Valid", audio.astype(np.float32)


def authenticate_voice(audio_array: np.ndarray, user_id: str) -> Tuple[bool, float, str]:
    """
    Authenticate a voice sample against an enrolled user.
    Returns: (is_authenticated, score, decision)
    """
    try:
        from app.core.model_loader import get_verifier
        verifier = get_verifier()
        
        # Check if user is enrolled
        if not verifier.is_enrolled(user_id):
            logger.warning(f"User {user_id} not enrolled")
            return False, 0.0, "NOT_ENROLLED"
        
        # Perform verification
        logger.info(f"Verifying voice for {user_id}, audio length: {len(audio_array)}")
        result = verifier.verify(user_id, audio_array, 16000)
        score = result.get("score", 0.0)
        logger.info(f"Voice verification score for {user_id}: {score:.4f}")
        
        # Use configured threshold from the verifier
        # This ensures we respect the global security setting
        algo_threshold = verifier.threshold
        
        if score >= algo_threshold:
            logger.info(f"ACCEPT: {user_id} with score {score:.4f} (>= {algo_threshold})")
            return True, score, "ACCEPT"
        elif score >= (algo_threshold - 0.12): # Gray area
            logger.info(f"UNCERTAIN: {user_id} with score {score:.4f}")
            return False, score, "UNCERTAIN"
        else:
            logger.info(f"REJECT: {user_id} with score {score:.4f}")
            return False, score, "REJECT"
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return False, 0.0, f"ERROR: {str(e)}"


def enroll_voice(audio_samples: List[bytes], user_id: str, overwrite: bool = True) -> Tuple[bool, str]:
    """
    Enroll a user with multiple voice samples.
    Returns: (success, message)
    """
    try:
        from app.core.model_loader import get_verifier
        verifier = get_verifier()
        
        # Validate all samples first
        valid_samples = []
        sample_details = []
        
        for i, audio_bytes in enumerate(audio_samples):
            sample_id = f"s{i+1}"
            is_valid, message, audio = validate_audio(audio_bytes)
            
            if is_valid and audio is not None:
                valid_samples.append((audio, 16000))
                sample_details.append(f"{sample_id}:OK")
                logger.info(f"Sample {sample_id} valid: {len(audio)/16000:.2f}s")
            else:
                sample_details.append(f"{sample_id}:{message}")
                logger.warning(f"Sample {sample_id} invalid: {message}")
        
        if len(valid_samples) < 3:
            return False, f"Only {len(valid_samples)} valid samples (need 3). Details: {', '.join(sample_details)}"
        
        # Enroll user
        result = verifier.enroll_user(
            user_id=user_id,
            audio_samples=valid_samples,
            overwrite=overwrite
        )
        
        if result.get("success", False):
            return True, f"Enrolled with {len(valid_samples)} samples"
        else:
            return False, result.get("message", "Enrollment failed")
            
    except Exception as e:
        logger.error(f"Enrollment error: {e}")
        return False, str(e)
