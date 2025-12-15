# Voice Auth Working Model Backup
# ================================
# Date: 2025-12-15 23:38
# Status: Near Perfect

## Files Backed Up:
1. simple_auth_v1.py - Main auth script with sensitive mode
2. speaker_verification_v1.py - Speaker verification with RAW cosine similarity
3. config_v1.py - Config with threshold 0.35

## Key Settings:
- Audio Boost: 5.0x
- Threshold: 0.40 (in simple_auth)
- Uses RAW cosine similarity (not normalized)
- No minimum audio level check

## To Restore:
```
copy backup_working_model\simple_auth_v1.py simple_auth.py
copy backup_working_model\speaker_verification_v1.py speaker_verification.py
copy backup_working_model\config_v1.py config.py
```
