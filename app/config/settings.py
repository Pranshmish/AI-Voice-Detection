"""
Voice Auth API - Settings
"""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
MODELS_DIR = BASE_DIR / "models"
VOICEPRINTS_DIR = BASE_DIR / "voiceprints"

# Auth Settings
SPEAKER_THRESHOLD = float(os.getenv("SPEAKER_THRESHOLD", "0.40"))
AUDIO_BOOST = float(os.getenv("AUDIO_BOOST", "5.0"))
MAX_AUDIO_DURATION_SEC = int(os.getenv("MAX_AUDIO_DURATION_SEC", "5"))
SAMPLE_RATE = 16000

# API Settings
API_KEY = os.getenv("API_KEY", "dev-key-change-in-production")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

# Security
REQUIRE_HTTPS = os.getenv("REQUIRE_HTTPS", "false").lower() == "true"
