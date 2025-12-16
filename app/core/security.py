"""
Security Middleware - HACKATHON MODE (OPEN ACCESS)
"""
from fastapi import Request, Security
from fastapi.security import APIKeyHeader
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

# Hackathon Mode: No rate limits, no API keys
API_KEY = "open-access"

async def verify_api_key():
    """HACKATHON MODE: Always allow access."""
    return "open-access"

async def check_rate_limit(request: Request):
    """HACKATHON MODE: No rate limit."""
    pass

def validate_audio_size(content_length: int, max_size_mb: int = 10):
    """Generous size limit (10MB)."""
    pass
