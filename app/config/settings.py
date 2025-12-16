"""
API Settings - HACKATHON
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
MODELS_DIR = BASE_DIR / "models"
VOICEPRINTS_DIR = BASE_DIR / "voiceprints"

# Audio Config
SAMPLE_RATE = 16000
AUDIO_BOOST = 5.0
MAX_AUDIO_DURATION_SEC = 10 

# Model Config
SPEAKER_THRESHOLD = float(os.getenv("SPEAKER_THRESHOLD", "0.40"))

# Security (Disabled)
API_KEY = "open"
RATE_LIMIT_PER_MINUTE = 999999
REQUIRE_HTTPS = False
