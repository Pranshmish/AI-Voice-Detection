"""
Voice Auth API Settings
=======================
Production-ready configuration for Render deployment.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
MODELS_DIR = BASE_DIR / "models"
VOICEPRINTS_DIR = BASE_DIR / "voiceprints"

# Ensure directories exist
MODELS_DIR.mkdir(exist_ok=True)
VOICEPRINTS_DIR.mkdir(exist_ok=True)

# Audio Config
SAMPLE_RATE = 16000
MAX_AUDIO_DURATION_SEC = 10

# ECAPA-TDNN Thresholds (calibrated for real-world microphones)
# Lowered thresholds to account for microphone variability and environment noise
THRESHOLD_HIGH = 0.55  # High confidence
THRESHOLD_BORDERLINE = 0.40  # Medium confidence  
THRESHOLD_IMPOSTER = 0.25  # Likely imposter
SPEAKER_THRESHOLD = float(os.getenv("SPEAKER_THRESHOLD", "0.30"))

# Phrase matching (lowered for STT variations)
PHRASE_MATCH_THRESHOLD = 0.50

# STT Model (use 'tiny' for lightweight, 'base' for better accuracy)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# API Config
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", "8000"))  # Render uses PORT env var

# Security
API_KEY = os.getenv("API_KEY", "")  # Empty = no auth required
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT", "100"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
