"""
Model Loader - Singleton pattern for speaker verification model
"""
import sys
from pathlib import Path
from threading import Lock

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from speaker_verification import SpeakerVerifier
from app.config.settings import SPEAKER_THRESHOLD

_model_lock = Lock()
_verifier_instance = None


def get_verifier() -> SpeakerVerifier:
    """
    Get singleton SpeakerVerifier instance.
    Thread-safe lazy initialization.
    """
    global _verifier_instance
    
    if _verifier_instance is None:
        with _model_lock:
            if _verifier_instance is None:
                _verifier_instance = SpeakerVerifier(threshold=SPEAKER_THRESHOLD)
    
    return _verifier_instance


def is_model_loaded() -> bool:
    """Check if model is loaded."""
    return _verifier_instance is not None
