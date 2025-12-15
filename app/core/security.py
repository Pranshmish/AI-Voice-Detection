"""
Security Middleware - API key validation, rate limiting
"""
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

from app.config.settings import API_KEY, RATE_LIMIT_PER_MINUTE

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Simple in-memory rate limiting (use Redis in production)
_rate_limit_store = defaultdict(list)
_rate_limit_lock = asyncio.Lock()


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key."""
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return api_key


async def check_rate_limit(request: Request):
    """Check rate limit for IP."""
    client_ip = request.client.host
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=1)
    
    async with _rate_limit_lock:
        # Clean old entries
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store[client_ip]
            if t > window_start
        ]
        
        # Check limit
        if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later."
            )
        
        # Add current request
        _rate_limit_store[client_ip].append(now)


def validate_audio_size(content_length: int, max_size_mb: int = 5):
    """Validate audio file size."""
    max_bytes = max_size_mb * 1024 * 1024
    if content_length > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large. Max {max_size_mb}MB allowed."
        )
