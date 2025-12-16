# Deployment Guide - Render.com

## Quick Deploy

### 1. Push to GitHub
```bash
git add .
git commit -m "Production ready"
git push origin main
```

### 2. Create Render Web Service
1. Go to https://render.com
2. New → Web Service → Connect GitHub repo

### 3. Configure Settings

| Setting | Value |
|---------|-------|
| **Name** | voice-auth-api |
| **Region** | Oregon (US West) |
| **Branch** | main |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

### 4. Environment Variables (Optional)
```
SPEAKER_THRESHOLD=0.40
```

### 5. Deploy!

Click "Create Web Service" and wait ~5 minutes.

---

## Post-Deployment

### Test Endpoints
```bash
# Health check
curl https://your-app.onrender.com/api/v1/voice/health

# Get integration guide
curl https://your-app.onrender.com/integration
```

### API Docs
Visit: `https://your-app.onrender.com/docs`

---

## Notes

- **Cold Start**: Free tier may take 30-60s on first request
- **Models**: ECAPA-TDNN downloads on first run (~40MB)
- **Vosk Model**: Download manually or skip STT for faster deploy

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError | Check requirements.txt |
| Model download fails | Increase memory (512MB+) |
| Timeout | Increase request timeout |
