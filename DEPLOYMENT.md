# 🚀 Voice Auth API - Deployment Guide

## Option 1: Railway (Recommended - Free Tier)

### Steps:
1. **Create account:** https://railway.app
2. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   railway login
   ```
3. **Deploy:**
   ```bash
   cd "Voice Detection"
   railway init
   railway up
   ```
4. **Set Environment Variables in Railway Dashboard:**
   - `API_KEY=your-secure-key`
   - `SPEAKER_THRESHOLD=0.40`
   - `AUDIO_BOOST=5.0`

---

## Option 2: Render (Free Tier)

1. **Create account:** https://render.com
2. **New Web Service → Connect GitHub repo**
3. **Settings:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Add Environment Variables**

---

## Option 3: Docker + Any VPS

### Build & Run:
```bash
# Build image
docker build -t voice-auth-api .

# Run container
docker run -d \
  -p 8000:8000 \
  -e API_KEY=your-secure-key \
  -e SPEAKER_THRESHOLD=0.40 \
  -v $(pwd)/voiceprints:/app/voiceprints \
  --name voice-auth \
  voice-auth-api
```

### VPS Options:
- **DigitalOcean:** $4/month
- **Linode:** $5/month
- **AWS EC2:** Free tier available
- **Google Cloud Run:** Pay per use

---

## Option 4: Hugging Face Spaces (Free - Limited)

1. Create Space at https://huggingface.co/spaces
2. Select "Docker" SDK
3. Upload your files
4. It will auto-deploy

---

## Option 5: Local Network (For Testing)

### Expose to LAN:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Access from other devices: `http://YOUR_IP:8000`

### Expose to Internet (Ngrok):
```bash
# Install ngrok
pip install pyngrok

# Run
ngrok http 8000
```
Get public URL like: `https://abc123.ngrok.io`

---

## Production Checklist

### Security:
- [ ] Change `API_KEY` to strong random string
- [ ] Enable HTTPS (use reverse proxy like Nginx)
- [ ] Set `REQUIRE_HTTPS=true`
- [ ] Configure CORS for your frontend domain

### Performance:
- [ ] Use Gunicorn with multiple workers:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
  ```
- [ ] Add Redis for rate limiting (production)
- [ ] Set up monitoring (Prometheus/Grafana)

### Storage:
- [ ] Mount persistent volume for `/voiceprints`
- [ ] Backup voiceprints regularly

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | Yes | dev-key... | API authentication |
| `SPEAKER_THRESHOLD` | No | 0.40 | Voice match threshold |
| `AUDIO_BOOST` | No | 5.0 | Mic sensitivity |
| `RATE_LIMIT_PER_MINUTE` | No | 30 | Rate limit |
| `REQUIRE_HTTPS` | No | false | Force HTTPS |

---

## API Usage After Deployment

### Health Check:
```bash
curl https://YOUR_DOMAIN/api/v1/voice/health
```

### Authenticate:
```bash
curl -X POST "https://YOUR_DOMAIN/api/v1/voice/authenticate" \
  -H "X-API-Key: your-api-key" \
  -F "audio=@voice.wav" \
  -F "user_id=owner"
```

### Enroll:
```bash
curl -X POST "https://YOUR_DOMAIN/api/v1/voice/enroll" \
  -H "X-API-Key: your-api-key" \
  -F "audio_files=@s1.wav" \
  -F "audio_files=@s2.wav" \
  -F "audio_files=@s3.wav" \
  -F "user_id=newuser"
```

---

## Quick Start Commands

```bash
# Local development
uvicorn app.main:app --reload

# Production (single worker)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Production (multiple workers)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Docker
docker-compose up -d
```
