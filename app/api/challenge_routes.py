"""
Challenge API Routes - Random Phrase Verification
-------------------------------------------------
Endpoints for challenge-response voice authentication.
"""
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import logging

from app.core.challenge import (
    create_session, get_session, verify_phrase, 
    update_session_trial, cleanup_expired_sessions
)
from app.core.stt import transcribe_audio, is_stt_available
from app.core.inference import authenticate_voice, validate_audio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/challenge", tags=["Challenge Auth"])


class ChallengeStartResponse(BaseModel):
    session_id: str
    phrase: str
    trials_remaining: int
    expires_in_seconds: int = 300
    stt_available: bool


class ChallengeVerifyResponse(BaseModel):
    success: bool
    speaker_match: bool
    phrase_match: bool
    spoken_text: str
    expected_phrase: str
    speaker_score: float
    phrase_score: float
    trials_remaining: int
    message: str


@router.post("/start", response_model=ChallengeStartResponse)
async def start_challenge(user_id: str = Form(...)):
    """
    Start a new challenge session.
    Returns a random phrase the user must speak.
    """
    cleanup_expired_sessions()
    
    session = create_session(user_id)
    
    return ChallengeStartResponse(
        session_id=session["session_id"],
        phrase=session["phrase"],
        trials_remaining=session["trials_remaining"],
        expires_in_seconds=300,
        stt_available=is_stt_available()
    )


@router.post("/verify", response_model=ChallengeVerifyResponse)
async def verify_challenge(
    session_id: str = Form(...),
    audio: UploadFile = File(..., description="Audio of user speaking the phrase")
):
    """
    Verify the challenge.
    Checks both:
    1. Speaker identity (ECAPA-TDNN)
    2. Spoken phrase matches (STT)
    """
    # Get session
    session = get_session(session_id)
    if not session:
        return ChallengeVerifyResponse(
            success=False,
            speaker_match=False,
            phrase_match=False,
            spoken_text="",
            expected_phrase="",
            speaker_score=0.0,
            phrase_score=0.0,
            trials_remaining=0,
            message="Session expired or invalid"
        )
    
    if session["status"] != "pending":
        return ChallengeVerifyResponse(
            success=False,
            speaker_match=False,
            phrase_match=False,
            spoken_text="",
            expected_phrase=session["phrase"],
            speaker_score=0.0,
            phrase_score=0.0,
            trials_remaining=session["trials_remaining"],
            message=f"Session already {session['status']}"
        )
    
    # Read and validate audio
    audio_bytes = await audio.read()
    is_valid, error, audio_array = validate_audio(audio_bytes)
    
    if not is_valid:
        return ChallengeVerifyResponse(
            success=False,
            speaker_match=False,
            phrase_match=False,
            spoken_text="",
            expected_phrase=session["phrase"],
            speaker_score=0.0,
            phrase_score=0.0,
            trials_remaining=session["trials_remaining"],
            message=f"Audio error: {error}"
        )
    
    # 1. Speaker Verification
    speaker_match, speaker_score, _ = authenticate_voice(audio_array, session["user_id"])
    
    # 2. Speech-to-Text (pass expected phrase as hint for better accuracy)
    spoken_text = transcribe_audio(audio_array, prompt_hint=f"Say: {session['phrase']}")
    
    # 3. Phrase Verification
    phrase_match, phrase_score = verify_phrase(spoken_text, session["phrase"])
    
    # Combined decision
    success = speaker_match and phrase_match
    
    # Update session
    updated_session = update_session_trial(session_id, success)
    trials_left = updated_session["trials_remaining"] if updated_session else 0
    
    # Generate message
    if success:
        message = "✅ Verified! Voice + Phrase matched."
    elif not speaker_match and not phrase_match:
        message = f"❌ Failed: Voice mismatch + Wrong phrase. {trials_left} tries left."
    elif not speaker_match:
        message = f"❌ Failed: Voice doesn't match. {trials_left} tries left."
    elif not phrase_match:
        message = f"❌ Failed: Wrong phrase spoken. {trials_left} tries left."
    else:
        message = f"❌ Failed. {trials_left} tries left."
    
    return ChallengeVerifyResponse(
        success=success,
        speaker_match=speaker_match,
        phrase_match=phrase_match,
        spoken_text=spoken_text,
        expected_phrase=session["phrase"],
        speaker_score=round(speaker_score, 3),
        phrase_score=round(phrase_score, 3),
        trials_remaining=trials_left,
        message=message
    )


@router.get("/session/{session_id}")
async def get_session_status(session_id: str):
    """Get current session status."""
    session = get_session(session_id)
    if not session:
        return {"error": "Session not found or expired"}
    return session


@router.post("/verify-with-text", response_model=ChallengeVerifyResponse)
async def verify_challenge_with_text(
    session_id: str = Form(...),
    spoken_text: str = Form(..., description="Text from browser STT"),
    audio: UploadFile = File(..., description="Audio of user speaking the phrase")
):
    """
    Verify the challenge using FRONTEND STT.
    Uses browser's Web Speech API for text (more accurate).
    Backend only verifies:
    1. Speaker identity (ECAPA-TDNN)
    2. Phrase matching (comparing frontend STT text with expected phrase)
    """
    logger.info(f"Verify with frontend STT: '{spoken_text}'")
    
    # Get session
    session = get_session(session_id)
    if not session:
        return ChallengeVerifyResponse(
            success=False,
            speaker_match=False,
            phrase_match=False,
            spoken_text=spoken_text,
            expected_phrase="",
            speaker_score=0.0,
            phrase_score=0.0,
            trials_remaining=0,
            message="Session expired or invalid"
        )
    
    if session["status"] != "pending":
        return ChallengeVerifyResponse(
            success=False,
            speaker_match=False,
            phrase_match=False,
            spoken_text=spoken_text,
            expected_phrase=session["phrase"],
            speaker_score=0.0,
            phrase_score=0.0,
            trials_remaining=session["trials_remaining"],
            message=f"Session already {session['status']}"
        )
    
    # Read and validate audio
    audio_bytes = await audio.read()
    is_valid, error, audio_array = validate_audio(audio_bytes)
    
    if not is_valid:
        return ChallengeVerifyResponse(
            success=False,
            speaker_match=False,
            phrase_match=False,
            spoken_text=spoken_text,
            expected_phrase=session["phrase"],
            speaker_score=0.0,
            phrase_score=0.0,
            trials_remaining=session["trials_remaining"],
            message=f"Audio error: {error}"
        )
    
    # 1. Speaker Verification (ECAPA-TDNN)
    speaker_match, speaker_score, decision = authenticate_voice(audio_array, session["user_id"])
    logger.info(f"Speaker verification: match={speaker_match}, score={speaker_score:.3f}, decision={decision}")
    
    # 2. Phrase Verification (using FRONTEND STT text)
    phrase_match, phrase_score = verify_phrase(spoken_text, session["phrase"])
    logger.info(f"Phrase verification: match={phrase_match}, score={phrase_score:.2f}")
    
    # Combined decision
    success = speaker_match and phrase_match
    
    # Update session
    updated_session = update_session_trial(session_id, success)
    trials_left = updated_session["trials_remaining"] if updated_session else 0
    
    # Generate message
    if success:
        message = "✅ Verified! Voice + Phrase matched."
    elif not speaker_match and not phrase_match:
        message = f"❌ Failed: Voice mismatch + Wrong phrase. {trials_left} tries left."
    elif not speaker_match:
        message = f"❌ Failed: Voice doesn't match (score: {speaker_score:.2f}). {trials_left} tries left."
    elif not phrase_match:
        message = f"❌ Failed: Phrase mismatch (score: {phrase_score:.2f}). {trials_left} tries left."
    else:
        message = f"❌ Failed. {trials_left} tries left."
    
    return ChallengeVerifyResponse(
        success=success,
        speaker_match=speaker_match,
        phrase_match=phrase_match,
        spoken_text=spoken_text,
        expected_phrase=session["phrase"],
        speaker_score=round(speaker_score, 3),
        phrase_score=round(phrase_score, 3),
        trials_remaining=trials_left,
        message=message
    )
