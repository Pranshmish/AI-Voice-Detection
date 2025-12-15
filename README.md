# Voice Authentication API

Production-ready FastAPI microservice for voice authentication.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run API server
python -m uvicorn app.main:app --reload

# Or use the simple CLI
python simple_auth.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/voice/authenticate` | Authenticate user with voice |
| POST | `/api/v1/voice/enroll` | Enroll new user |
| GET | `/api/v1/voice/health` | Health check |

## Authentication

All endpoints require API key header:
```
X-API-Key: your-api-key
```

## Example Usage

### Authenticate
```bash
curl -X POST "http://localhost:8000/api/v1/voice/authenticate" \
  -H "X-API-Key: dev-key-change-in-production" \
  -F "audio=@voice.wav" \
  -F "user_id=user123"
```

### Enroll
```bash
curl -X POST "http://localhost:8000/api/v1/voice/enroll" \
  -H "X-API-Key: dev-key-change-in-production" \
  -F "audio_files=@sample1.wav" \
  -F "audio_files=@sample2.wav" \
  -F "audio_files=@sample3.wav" \
  -F "user_id=user123"
```

## Project Structure

```
Voice Detection/
├── app/
│   ├── main.py              # FastAPI application
│   ├── api/routes.py        # API endpoints
│   ├── core/
│   │   ├── model_loader.py  # Singleton model loader
│   │   ├── inference.py     # Authentication logic
│   │   └── security.py      # API key & rate limiting
│   ├── schemas/             # Pydantic models
│   └── config/settings.py   # Configuration
├── speaker_verification.py  # Core ML model
├── config.py               # Model config
├── simple_auth.py          # CLI for testing
├── voiceprints/            # Enrolled user data
├── models/                 # Pre-trained models
└── backup_working_model/   # Backup of working model
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| API_KEY | dev-key-change-in-production | API authentication key |
| SPEAKER_THRESHOLD | 0.40 | Voice match threshold |
| AUDIO_BOOST | 5.0 | Microphone sensitivity |
| RATE_LIMIT_PER_MINUTE | 30 | API rate limit |

## Docker

```bash
docker build -t voice-auth .
docker run -p 8000:8000 voice-auth
```
