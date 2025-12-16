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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: Load model
    logger.info("Starting Voice Auth API...")
    
    from app.core.model_loader import get_verifier
    try:
        verifier = get_verifier()
        logger.info("Speaker verification model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Voice Auth API...")


# Create app
app = FastAPI(
    title="Voice Authentication API",
    description="Production-ready voice authentication microservice",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
from app.api.routes import router as auth_router
from app.api.websocket import router as ws_router
from app.api.challenge_routes import router as challenge_router
from app.api.integration_guide import router as guide_router

app.include_router(auth_router)
app.include_router(ws_router)
app.include_router(challenge_router)
app.include_router(guide_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Voice Authentication API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
