# 🎤 Voice Authentication API

Production-ready voice authentication microservice with **Challenge-Response anti-replay protection**.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/voice/health` | GET | Health check |
| `/api/v1/voice/enroll` | POST | Enroll user (3+ samples) |
| `/api/v1/voice/authenticate` | POST | Simple voice auth |
| `/api/v1/challenge/start` | POST | Start challenge session |
| `/api/v1/challenge/verify` | POST | Verify challenge (RECOMMENDED) |
| `/ws/voice-stream` | WebSocket | Real-time streaming |
| `/integration` | GET | **Frontend integration guide (JSON)** |
| `/docs` | GET | Interactive API docs |

## 🛡️ Security: Challenge-Response Flow

1. **Start Challenge**: Get random phrase (e.g., "five red birds")
2. **User Speaks**: Display phrase, record user speaking it
3. **Verify**: Checks BOTH voice identity AND spoken words
4. **Anti-Replay**: Random phrases prevent recording attacks!

## 📱 Frontend Integration

Visit `/integration` for complete JSON documentation with code examples.

```javascript
// Quick Example
const challenge = await fetch('/api/v1/challenge/start', {
    method: 'POST',
    body: new URLSearchParams({ user_id: 'user123' })
}).then(r => r.json());

// Show phrase to user: challenge.phrase
// Record audio, then verify...
```

## 🌐 Deploy to Render

1. Push to GitHub
2. Connect to Render.com
3. Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Deploy! 🚀

## 📊 Tech Stack

- **Speaker Verification**: ECAPA-TDNN (SpeechBrain)
- **Speech-to-Text**: Vosk (offline)
- **API Framework**: FastAPI
- **Real-time**: WebSocket streaming

---
Made for **Hackathon 2024** 🏆
