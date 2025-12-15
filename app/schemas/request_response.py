"""
Request/Response Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


class AuthRequest(BaseModel):
    """Voice authentication request."""
    user_id: str = Field(..., min_length=1, max_length=50, description="User identifier")
    session_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Session ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "session_id": "abc-123-def"
            }
        }


class EnrollRequest(BaseModel):
    """Voice enrollment request."""
    user_id: str = Field(..., min_length=1, max_length=50, description="User identifier to enroll")
    overwrite: bool = Field(default=False, description="Overwrite existing enrollment")


class AuthResponse(BaseModel):
    """Voice authentication response."""
    authenticated: bool = Field(..., description="Whether user is authenticated")
    spoof_detected: bool = Field(default=False, description="Whether spoof/replay was detected")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    decision: Literal["AUTHENTIC", "IMPOSTER", "SPOOF", "REVIEW_REQUIRED", "ERROR"] = Field(..., description="Decision label")
    message: str = Field(..., description="Human readable message")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "authenticated": True,
                "spoof_detected": False,
                "confidence_score": 0.85,
                "decision": "AUTHENTIC",
                "message": "User authenticated successfully",
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-12-15T18:30:00.000Z"
            }
        }


class EnrollResponse(BaseModel):
    """Voice enrollment response."""
    success: bool
    user_id: str
    message: str
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    model_loaded: bool = True
    version: str = "1.0.0"
