"""
Configuration for Free Secure Voice Command Auth System
========================================================
Fully local, on-device voice authentication using:
- PyAnnote for VAD/diarization
- Librosa for feature extraction  
- SpeechBrain ECAPA-TDNN for speaker verification
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================
# Project Paths
# ============================================================
PROJECT_ROOT = Path(__file__).parent
LOGS_DIR = PROJECT_ROOT / "logs"
SAMPLES_DIR = PROJECT_ROOT / "samples"
MODELS_DIR = PROJECT_ROOT / "models"
USER_PROFILES_DIR = PROJECT_ROOT / "voiceprints"
USER_PROFILES_FILE = USER_PROFILES_DIR / "profiles.json"
EMBEDDINGS_DIR = USER_PROFILES_DIR / "embeddings"

# Create directories if they don't exist
for directory in [LOGS_DIR, SAMPLES_DIR, MODELS_DIR, USER_PROFILES_DIR, EMBEDDINGS_DIR]:
    directory.mkdir(exist_ok=True)

# ============================================================
# Audio Capture Settings (Stage 0)
# ============================================================
AUDIO_SAMPLE_RATE = 16000       # 16 kHz as required
AUDIO_CHANNELS = 1              # Mono
AUDIO_FORMAT = "WAV"
MIN_DURATION_SECONDS = 1.5      # Minimum acceptable duration
MAX_DURATION_SECONDS = 4.0      # Maximum recording duration
COMMAND_DURATION_SECONDS = 3.0  # Default command recording duration

# ============================================================
# Wake Word Settings
# ============================================================
WAKE_WORD_MODEL = "hey_jarvis"  # Default wake word model
WAKE_WORD_THRESHOLD = 0.5       # Detection confidence threshold
WAKE_WORD_LISTEN_TIMEOUT = 30   # Seconds to listen for wake word

# ============================================================
# Pre-Check Settings (Stage 1)
# ============================================================
ENERGY_THRESHOLD = 0.002        # RMS energy threshold for speech detection (lowered for quiet mics)
SILENCE_THRESHOLD = 0.0005      # Below this is considered silence
VAD_AGGRESSIVENESS = 2          # 0-3, higher = more aggressive filtering

# ============================================================
# Liveness Detection Settings (Stage 2)
# ============================================================
LIVENESS_THRESHOLD = 0.6        # Score above this is considered live

# Feature weights for liveness scoring
LIVENESS_WEIGHTS = {
    "mfcc_variation": 0.25,
    "energy_variation": 0.20,
    "zcr_variation": 0.15,
    "spectral_variation": 0.20,
    "segment_naturalness": 0.20
}

# Thresholds for individual liveness features
MFCC_STD_THRESHOLD = 2.0        # Minimum MFCC std for live speech
ENERGY_COV_THRESHOLD = 0.3      # Minimum coefficient of variation for energy
ZCR_VARIATION_THRESHOLD = 0.1   # Minimum ZCR variation

# ============================================================
# SpeechBrain Speaker Verification Settings (Stages 3 & 4)
# ============================================================
SPEECHBRAIN_MODEL = "speechbrain/spkrec-ecapa-voxceleb"
EMBEDDING_DIM = 192             # ECAPA-TDNN embedding dimension

# Speaker verification threshold (RAW cosine similarity)
VERIFICATION_THRESHOLD = 0.30   # ADJUSTED: Blocks intruders but allows owner variability
# Same speaker typically: 0.30 - 0.70
# Different speakers: -0.10 - 0.25
# Threshold 0.30 is the precision calibration point

# Enrollment requirements
MIN_ENROLLMENT_SAMPLES = 3      # Minimum audio samples for enrollment
MAX_ENROLLMENT_SAMPLES = 5      # Recommended maximum
MIN_ENROLLMENT_DURATION = 5     # Minimum seconds per sample
MAX_ENROLLMENT_DURATION = 15    # Maximum seconds per sample

# ============================================================
# PyAnnote Settings
# ============================================================
# HuggingFace token for pyannote models (required for some models)
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")

# Diarization parameters
PYANNOTE_MIN_SPEAKERS = 1
PYANNOTE_MAX_SPEAKERS = 1       # We expect single speaker

# ============================================================
# Logging Settings
# ============================================================
AUTH_LOG_FILE = LOGS_DIR / "auth_log.json"
DEBUG_LOG_FILE = LOGS_DIR / "debug.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================================
# Decision Engine Settings (Stage 5)
# ============================================================
STEP_UP_AUTH_ENABLED = True     # Enable step-up authentication option
HIGH_RISK_COMMANDS = [
    "unlock", "open", "delete", "transfer", "send", "pay"
]

# ============================================================
# Utility Functions
# ============================================================
def validate_config() -> dict:
    """Validate configuration and return status."""
    issues = []
    warnings = []
    
    if not HUGGINGFACE_TOKEN:
        warnings.append("HUGGINGFACE_TOKEN not set - some PyAnnote models may not work")
    
    # Check if models directory exists
    if not MODELS_DIR.exists():
        issues.append(f"Models directory does not exist: {MODELS_DIR}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "speechbrain_model": SPEECHBRAIN_MODEL,
        "pyannote_token_set": bool(HUGGINGFACE_TOKEN)
    }


def get_config_summary() -> dict:
    """Return a summary of current configuration."""
    return {
        "audio": {
            "sample_rate": AUDIO_SAMPLE_RATE,
            "channels": AUDIO_CHANNELS,
            "min_duration": MIN_DURATION_SECONDS,
            "max_duration": MAX_DURATION_SECONDS
        },
        "thresholds": {
            "liveness": LIVENESS_THRESHOLD,
            "verification": VERIFICATION_THRESHOLD,
            "energy": ENERGY_THRESHOLD
        },
        "speaker_verification": {
            "backend": "SpeechBrain ECAPA-TDNN (local)",
            "model": SPEECHBRAIN_MODEL,
            "embedding_dim": EMBEDDING_DIM
        },
        "paths": {
            "logs": str(LOGS_DIR),
            "samples": str(SAMPLES_DIR),
            "models": str(MODELS_DIR),
            "voiceprints": str(USER_PROFILES_DIR)
        }
    }


if __name__ == "__main__":
    # Print configuration summary when run directly
    import json
    print("=" * 60)
    print("Voice Auth Configuration Summary")
    print("=" * 60)
    print(json.dumps(get_config_summary(), indent=2))
    print("\nValidation:")
    print(json.dumps(validate_config(), indent=2))
