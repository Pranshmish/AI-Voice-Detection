"""
Voice Authentication API
========================
Production-ready FastAPI microservice for voice authentication.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.routes import router as voice_router
from app.api.challenge_routes import router as challenge_router
from app.api.stt_routes import router as stt_router
from app.api.websocket import router as websocket_router
from app.core.model_loader import get_verifier, is_model_loaded

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Voice Auth API...")
    
    # Pre-load model on startup
    try:
        verifier = get_verifier()
        logger.info("Speaker verification model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
    
    yield
    
    logger.info("Shutting down Voice Auth API...")


# Create FastAPI app
app = FastAPI(
    title="Voice Authentication API",
    description="AI-powered voice authentication with anti-spoofing",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(voice_router)
app.include_router(challenge_router)
app.include_router(stt_router)
app.include_router(websocket_router)


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Voice Authentication API",
        "version": "1.0.0",
        "status": "running",
        "model_loaded": is_model_loaded(),
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": is_model_loaded()
    }


@app.get("/status")
async def status():
    """Status endpoint for compatibility with Vibrations page."""
    return {
        "status": "voice_auth_only",
        "model_trained": False,
        "samples": {},
        "total_samples": 0,
        "message": "Voice Auth API - Vibration detection requires separate backend."
    }


# ============== STUB ENDPOINTS FOR VIBRATIONS PAGE COMPATIBILITY ==============

@app.get("/dataset_status")
async def dataset_status():
    """Stub for Vibrations page."""
    return {"dual_dataset": {}, "sample_counts": {}, "mlp_model": None}


@app.get("/available_models")
async def available_models():
    """Stub for Vibrations page."""
    return {"models": [], "active_model": None}


@app.get("/model_status")
async def model_status():
    """Stub for Vibrations page."""
    return {"models": {}, "active_model": None}


@app.get("/dataset")
async def dataset():
    """Stub for Vibrations page."""
    return {"persons": [], "total_samples": 0, "model_status": "not_available"}


@app.get("/dataset/list")
async def dataset_list():
    """Stub for Vibrations page."""
    return {"datasets": [], "total_samples": 0, "total_datasets": 0}
