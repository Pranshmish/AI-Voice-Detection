"""
STT API Routes - Speech to Text using Whisper
==============================================
Provides transcription endpoint for frontend fallback
when browser SpeechRecognition fails.
"""
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
import logging

from app.core.stt import transcribe_audio, is_stt_available
from app.core.inference import validate_audio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/stt", tags=["Speech to Text"])


class TranscribeResponse(BaseModel):
    success: bool
    text: str
    message: str = ""


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    audio: UploadFile = File(..., description="Audio file to transcribe")
):
    """
    Transcribe audio to text using Whisper.
    Use this as fallback when browser SpeechRecognition fails.
    """
    logger.info(f"STT request: file={audio.filename}, size={audio.size}")
    
    # Read and validate audio
    audio_bytes = await audio.read()
    logger.info(f"Audio bytes received: {len(audio_bytes)}")
    
    is_valid, error, audio_array = validate_audio(audio_bytes)
    
    if not is_valid:
        logger.error(f"Audio validation failed: {error}")
        return TranscribeResponse(
            success=False,
            text="",
            message=f"Audio error: {error}"
        )
    
    # Check if STT is available
    if not is_stt_available():
        logger.warning("Whisper STT not available")
        return TranscribeResponse(
            success=False,
            text="",
            message="STT not available on server"
        )
    
    # Transcribe
    try:
        text = transcribe_audio(audio_array, sample_rate=16000)
        logger.info(f"Transcription result: '{text}'")
        
        return TranscribeResponse(
            success=True,
            text=text,
            message="OK" if text else "No speech detected"
        )
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return TranscribeResponse(
            success=False,
            text="",
            message=str(e)
        )


@router.get("/status")
async def stt_status():
    """Check if STT service is available."""
    return {
        "available": is_stt_available(),
        "engine": "whisper"
    }
