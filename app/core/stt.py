"""
Speech-to-Text Module using OpenAI Whisper
-------------------------------------------
Converts audio to text for challenge phrase verification.
Uses 'tiny' or 'base' model for lightweight deployment.
"""
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

# Whisper model (loaded lazily)
_whisper_model = None
_whisper_available = False

# Model selection: tiny (39MB), base (74MB), small (244MB)
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")


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
    Convert audio to text with improved accuracy.
    
    Args:
        audio: Audio samples (float32, mono)
        sample_rate: Sample rate (default 16000)
        prompt_hint: Optional hint about expected content (improves accuracy)
        
    Returns:
        Transcribed text
    """
    global _whisper_model, _whisper_available
    
    if _whisper_model is None:
        _load_whisper()
    
    if not _whisper_available or _whisper_model is None:
        return ""
    
    try:
        import whisper
        
        # Ensure float32
        audio_float = audio.astype(np.float32)
        
        # Normalize audio for better recognition
        max_val = np.max(np.abs(audio_float))
        if max_val > 0.01:
            audio_float = audio_float / max_val * 0.9
        
        # Pad/trim to 30 seconds
        audio_padded = whisper.pad_or_trim(audio_float)
        
        # Create mel spectrogram
        mel = whisper.log_mel_spectrogram(audio_padded).to(_whisper_model.device)
        
        # Enhanced decoding options for better accuracy
        options = whisper.DecodingOptions(
            language="en",
            without_timestamps=True,
            fp16=False,  # CPU compatibility
            # Prompt hint helps with expected words
            prompt=prompt_hint if prompt_hint else "voice authentication phrase: ",
            # Better beam search for accuracy
            beam_size=5,
            best_of=3,
            # Temperature settings for more deterministic output
            temperature=0.0,
        )
        result = whisper.decode(_whisper_model, mel, options)
        
        text = result.text.strip()
        
        # Clean up common STT artifacts
        text = text.replace(",", "").replace(".", "").replace("!", "").replace("?", "")
        text = " ".join(text.split())  # Normalize whitespace
        
        logger.info(f"STT Result: '{text}'")
        return text
        
    except Exception as e:
        logger.error(f"STT error: {e}")
        return ""


def is_stt_available() -> bool:
    """Check if STT is available."""
    global _whisper_model, _whisper_available
    if _whisper_model is None:
        _load_whisper()
    return _whisper_available
