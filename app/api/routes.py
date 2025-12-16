"""
API Routes - HACKATHON MODE (No Auth)
"""
from fastapi import APIRouter, UploadFile, File, Form, Request
from typing import List
import logging

from app.schemas.request_response import AuthResponse, EnrollResponse, HealthResponse
from app.core.inference import authenticate_voice, enroll_voice, validate_audio
from app.core.model_loader import is_model_loaded

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/voice", tags=["Voice This Hackathon"])

@router.post("/authenticate", response_model=AuthResponse)
async def authenticate(
    request: Request,
    audio: UploadFile = File(..., description="WAV/MP3 Audio"),
    user_id: str = Form(..., description="User ID"),
    session_id: str = Form(default="", description="Optional Sess ID")
):
    """
    Authenticate User (Open Access)
    """
    logger.info(f"Auth: {user_id}")
    
    # Read/Validate
    audio_bytes = await audio.read()
    is_valid, error, audio_array = validate_audio(audio_bytes)
    
    if not is_valid:
        return AuthResponse(
            authenticated=False, spoof_detected=False, confidence_score=0.0,
            decision="ERROR", message=error
        )
    
    # Auth
    try:
        is_auth, score, decision = authenticate_voice(audio_array, user_id)
        return AuthResponse(
            authenticated=is_auth, spoof_detected=False, confidence_score=score,
            decision=decision,
            message="Authenticated" if is_auth else f"Failed: {decision}"
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        return AuthResponse(
            authenticated=False, spoof_detected=False, confidence_score=0.0,
            decision="ERROR", message="Server Error"
        )

@router.post("/enroll", response_model=EnrollResponse)
async def enroll(
    request: Request,
    audio_files: List[UploadFile] = File(..., description="3+ Voice Samples"),
    user_id: str = Form(..., description="User ID"),
    overwrite: bool = Form(default=True, description="Overwrite?")
):
    """
    Enroll User (Open Access)
    """
    if len(audio_files) < 3:
        return EnrollResponse(success=False, user_id=user_id, message="Need 3 samples!")
    
    samples = [await f.read() for f in audio_files]
    success, msg = enroll_voice(samples, user_id, overwrite)
    
    return EnrollResponse(success=success, user_id=user_id, message=msg)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ready_for_demo", model_loaded=is_model_loaded())
