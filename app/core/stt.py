"""
Speech-to-Text Module using Vosk (Offline STT)
----------------------------------------------
Converts audio to text for challenge phrase verification.
"""
import numpy as np
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Vosk model (loaded lazily)
_vosk_model = None
_vosk_available = False

def _load_vosk():
    """Load Vosk model for offline STT."""
    global _vosk_model, _vosk_available
    
    try:
        from vosk import Model, KaldiRecognizer
        
        # Try to find model
        model_paths = [
            Path("models/vosk-model-small-en-us-0.15"),
            Path("models/vosk-model-en-us-0.22"),
            Path("vosk-model-small-en-us-0.15"),
            Path.home() / ".cache/vosk/vosk-model-small-en-us-0.15"
        ]
        
        model_path = None
        for p in model_paths:
            if p.exists():
                model_path = p
                break
        
        if model_path:
            _vosk_model = Model(str(model_path))
            _vosk_available = True
            logger.info(f"Vosk loaded from: {model_path}")
        else:
            logger.warning("Vosk model not found. STT disabled.")
            _vosk_available = False
            
    except ImportError:
        logger.warning("Vosk not installed. Using fallback STT.")
        _vosk_available = False


def transcribe_audio(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Convert audio to text.
    
    Args:
        audio: Audio samples (float32, mono)
        sample_rate: Sample rate (default 16000)
        
    Returns:
        Transcribed text
    """
    global _vosk_model, _vosk_available
    
    # Try Vosk first
    if _vosk_model is None:
        _load_vosk()
    
    if _vosk_available and _vosk_model:
        try:
            from vosk import KaldiRecognizer
            
            # Convert to int16 for Vosk
            audio_int16 = (audio * 32767).astype(np.int16)
            
            rec = KaldiRecognizer(_vosk_model, sample_rate)
            rec.SetWords(True)
            
            # Process audio
            rec.AcceptWaveform(audio_int16.tobytes())
            result = json.loads(rec.FinalResult())
            
            text = result.get("text", "")
            logger.info(f"STT Result: {text}")
            return text
            
        except Exception as e:
            logger.error(f"Vosk error: {e}")
    
    # Fallback: No STT available
    logger.warning("STT not available - returning empty")
    return ""


def is_stt_available() -> bool:
    """Check if STT is available."""
    global _vosk_model, _vosk_available
    if _vosk_model is None:
        _load_vosk()
    return _vosk_available
