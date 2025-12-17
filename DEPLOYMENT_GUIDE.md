# Voice Authentication API - Deployment Guide

## 🚀 Quick Deploy to Render

### Option 1: One-Click Deploy
1. Push code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Render will auto-detect `render.yaml` and deploy

### Option 2: Manual Setup
1. Create new Web Service on Render
2. Connect repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`
5. Add environment variables (see below)

## ⚙️ Environment Variables

Set these in Render Dashboard → Environment:

```bash
# Model Configuration
WHISPER_MODEL=tiny              # Options: tiny (39MB), base (74MB), small (244MB)
SPEAKER_THRESHOLD=0.65          # ECAPA-TDNN threshold

# API Configuration
PORT=8000                        # Render auto-sets this
CORS_ORIGINS=*                   # Configure for production

# Optional
API_KEY=                         # Leave empty for no auth
RATE_LIMIT=100                   # Requests per minute
```

## 📦 Minimal Deployment (Recommended)

For lightweight deployment on free tier:
- Use `WHISPER_MODEL=tiny` (fastest, 39MB)
- Single worker (`-w 1`)
- Total memory: ~800MB

## 🧪 Local Testing

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Locally
```bash
# Development
python -m uvicorn app.main:app --reload --port 8000

# Production mode
gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 3. Test Endpoints
```bash
# Health check
curl http://localhost:8000/api/v1/voice/health

# Enroll user (send 3 audio files)
curl -X POST http://localhost:8000/api/v1/voice/enroll \
  -F "user_id=test_user" \
  -F "audio_files=@sample1.wav" \
  -F "audio_files=@sample2.wav" \
  -F "audio_files=@sample3.wav"

# Authenticate
curl -X POST http://localhost:8000/api/v1/voice/authenticate \
  -F "user_id=test_user" \
  -F "audio=@test.wav"

# Challenge auth (phrase verification)
curl -X POST http://localhost:8000/api/v1/challenge/start \
  -F "user_id=test_user"
```

## 🔒 Security Checklist

- [ ] Set CORS_ORIGINS to your frontend domain
- [ ] Enable API_KEY for authentication
- [ ] Use HTTPS only in production
- [ ] Set appropriate RATE_LIMIT
- [ ] Don't commit .env files
- [ ] Monitor API usage on Render dashboard

## 📊 Performance

### Expected Response Times (Render Free Tier):
- Health check: ~50ms
- Enrollment (3 samples): ~2-3s
- Authentication: ~500ms-1s
- Challenge verification: ~1-2s (includes STT)

### Memory Usage:
- Base: ~400MB
- With Whisper tiny: ~800MB
- With Whisper base: ~1.2GB
- With Whisper small: ~1.8GB

## 🐛 Troubleshooting

### Build Fails
- Check `requirements.txt` versions
- Ensure Python 3.11 in `Dockerfile`
- Check Render build logs

### Out of Memory
- Use `WHISPER_MODEL=tiny`
- Reduce worker count to 1
- Upgrade to paid tier

### Slow STT
- Use smaller Whisper model
- Consider disabling STT for basic auth

### Model Not Loading
- Check file paths in deployment
- Verify model downloads properly
- Check Render build logs

## 📚 API Documentation

After deployment, visit:
- **Docs**: `https://your-app.onrender.com/docs`
- **ReDoc**: `https://your-app.onrender.com/redoc`
- **Health**: `https://your-app.onrender.com/api/v1/voice/health`

## 🎯 Next Steps

1. Test locally: `python -m uvicorn app.main:app --reload`
2. Push to GitHub
3. Deploy to Render
4. Test production endpoint
5. Configure frontend to use API
6. Monitor usage and errors

---

**Need help?** Check Render logs or API documentation at `/docs`
