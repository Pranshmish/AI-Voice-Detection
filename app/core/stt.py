"""
Speech-to-Text Module using OpenAI Whisper
-------------------------------------------
Simple, reliable STT for voice commands.
"""
import numpy as np
import logging
import os
import tempfile
import soundfile as sf

logger = logging.getLogger(__name__)

# Whisper model (loaded lazily)
_whisper_model = None
_whisper_available = False

# Model selection: tiny (39MB), base (74MB), small (244MB)
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "tiny")  # tiny is 5x faster


def _load_whisper():
    """Load Whisper model for STT."""
    global _whisper_model, _whisper_available
    
    try:
        import whisper
        
        logger.info(f"Loading Whisper '{WHISPER_MODEL_NAME}' model...")
        _whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
        _whisper_available = True
        logger.info("Whisper STT loaded successfully")
        
    except ImportError:
        logger.warning("Whisper not installed. Run: pip install openai-whisper")
        _whisper_available = False
    except Exception as e:
        logger.error(f"Whisper load failed: {e}")
        _whisper_available = False


def transcribe_audio(audio: np.ndarray, sample_rate: int = 16000, prompt_hint: str = "") -> str:
    """
    Convert audio to text using Whisper.
    Uses the simpler transcribe() method for better results.
    
    Args:
        audio: Audio samples (float32, mono)
        sample_rate: Sample rate (default 16000)
        prompt_hint: Optional hint about expected content
        
    Returns:
        Transcribed text
    """
    global _whisper_model, _whisper_available
    print(f">>> TRANSCRIBE_AUDIO CALLED: audio_len={len(audio)}, sample_rate={sample_rate}") # ENTRY DEBUG
    
    if _whisper_model is None:
        _load_whisper()
    
    if not _whisper_available or _whisper_model is None:
        logger.error("Whisper model not available")
        return ""
    
    try:
        # Log audio stats
        max_val = np.max(np.abs(audio))
        rms = np.sqrt(np.mean(audio**2))
        logger.info(f"STT input: {len(audio)} samples, max={max_val:.4f}, rms={rms:.4f}")
        
        # Ensure float32 and normalize
        audio_float = audio.astype(np.float32)
        
        # Check if audio has content
        if max_val < 0.0001:
            logger.warning(f"Audio is silent (max={max_val})")
            return ""
        
        # Normalize to [-1, 1] range
        if max_val > 0:
            audio_float = audio_float / max_val * 0.95
        
        # Pad or trim to 30 seconds (Whisper's expected input length)
        # Whisper expects audio at 16kHz
        target_length = sample_rate * 30  # 30 seconds
        if len(audio_float) < target_length:
            # Pad with zeros
            audio_float = np.pad(audio_float, (0, target_length - len(audio_float)))
        else:
            # Trim to 30 seconds
            audio_float = audio_float[:target_length]
        
        # Pass audio directly to Whisper (bypasses ffmpeg requirement)
        print(f"DEBUG STT: Calling whisper.transcribe() with numpy array ({len(audio_float)} samples)...")
        result = _whisper_model.transcribe(
            audio_float,  # Pass numpy array directly, NOT a file path
            language="en",
            initial_prompt=prompt_hint,
            fp16=False,
            verbose=False
        )
        print(f"DEBUG STT: Whisper returned: {result}")
        
        text = result.get("text", "").strip()
        print(f"DEBUG STT RAW: '{text}'") # DEBUG
        logger.info(f"STT raw result: '{text}'")
        
        # Basic cleanup - remove punctuation
        for char in ',.!?;:':
            text = text.replace(char, '')
        text = ' '.join(text.split())  # Normalize whitespace
        
        # Only filter obvious hallucinations (short generic phrases)
        hallucinations = [
            "thank you for watching",
            "thanks for watching", 
            "please subscribe",
            "like and subscribe",
        ]
        text_lower = text.lower().strip()
        if text_lower in hallucinations:
            logger.info(f"Filtered hallucination: '{text}'")
            return ""
        
        logger.info(f"STT final: '{text}'")
        return text
        
    except Exception as e:
        logger.error(f"STT error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ""


def is_stt_available() -> bool:
    """Check if STT is available."""
    global _whisper_model, _whisper_available
    if _whisper_model is None:
        _load_whisper()
    return _whisper_available
