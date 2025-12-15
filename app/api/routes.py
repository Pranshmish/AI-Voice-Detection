"""
API Routes - Voice Authentication Endpoints
"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from typing import List
import logging

from app.schemas.request_response import AuthResponse, EnrollResponse, HealthResponse
from app.core.inference import authenticate_voice, enroll_voice, validate_audio, get_audio_hash
from app.core.security import verify_api_key, check_rate_limit
from app.core.model_loader import is_model_loaded

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/voice", tags=["Voice Authentication"])


@router.post("/authenticate", response_model=AuthResponse)
async def authenticate(
    request: Request,
    audio: UploadFile = File(..., description="WAV audio file"),
    user_id: str = Form(..., description="User ID to authenticate"),
    session_id: str = Form(default="", description="Optional session ID"),
    api_key: str = Depends(verify_api_key)
):
    """
    Authenticate a user via voice.
    
    - Validates audio format and duration
    - Compares against enrolled voiceprint
    - Returns authentication decision with confidence score
    """
    await check_rate_limit(request)
    
    # Read audio
    audio_bytes = await audio.read()
    audio_hash = get_audio_hash(audio_bytes)
    
    logger.info(f"Auth request: user={user_id}, audio_hash={audio_hash}")
    
    # Validate audio
    is_valid, error, audio_array = validate_audio(audio_bytes)
    if not is_valid:
        return AuthResponse(
            authenticated=False,
            spoof_detected=False,
            confidence_score=0.0,
            decision="ERROR",
            message=error
        )
    
    # Authenticate
    try:
        is_auth, score, decision = authenticate_voice(audio_array, user_id)
        
        return AuthResponse(
            authenticated=is_auth,
            spoof_detected=False,
            confidence_score=score,
            decision=decision,
            message="Authenticated" if is_auth else f"Authentication failed: {decision}"
        )
        
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return AuthResponse(
            authenticated=False,
            spoof_detected=False,
            confidence_score=0.0,
            decision="ERROR",
            message="Internal authentication error"
        )


@router.post("/enroll", response_model=EnrollResponse)
async def enroll(
    request: Request,
    audio_files: List[UploadFile] = File(..., description="3 WAV audio samples"),
    user_id: str = Form(..., description="User ID to enroll"),
    overwrite: bool = Form(default=False, description="Overwrite existing"),
    api_key: str = Depends(verify_api_key)
):
    """
    Enroll a new user with voice samples.
    
    Requires 3 audio samples for reliable voiceprint creation.
    """
    await check_rate_limit(request)
    
    if len(audio_files) < 3:
        return EnrollResponse(
            success=False,
            user_id=user_id,
            message="Need at least 3 audio samples"
        )
    
    # Read all audio files
    audio_samples = []
    for f in audio_files:
        audio_samples.append(await f.read())
    
    logger.info(f"Enroll request: user={user_id}, samples={len(audio_samples)}")
    
    # Enroll
    try:
        success, message = enroll_voice(audio_samples, user_id, overwrite)
        
        return EnrollResponse(
            success=success,
            user_id=user_id,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Enroll error: {e}")
        return EnrollResponse(
            success=False,
            user_id=user_id,
            message="Enrollment failed"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model_loaded=is_model_loaded()
    )
