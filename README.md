# Voice Auth API - Hackathon Edition 🚀

**Open Access** voice verification service.

## 🔗 Endpoints (No API Key Required)

| Endpoint | Method | Params |
|----------|--------|--------|
| `/api/v1/voice/enroll` | POST | `audio_files` (3), `user_id` |
| `/api/v1/voice/authenticate` | POST | `audio` (1), `user_id` |
| `/ws/voice-stream` | WS | Real-time verification |

## ⚡ Quick Usage

### Enroll a User
```bash
curl -X POST "https://ai-voice-detection-2.onrender.com/api/v1/voice/enroll" \
  -F "user_id=judge1" \
  -F "audio_files=@sample1.wav" \
  -F "audio_files=@sample2.wav" \
  -F "audio_files=@sample3.wav"
```

### Verify (REST)
```bash
curl -X POST "https://ai-voice-detection-2.onrender.com/api/v1/voice/authenticate" \
  -F "user_id=judge1" \
  -F "audio=@test.wav"
```

### Live Streaming (WebSocket)
1. Connect to `wss://ai-voice-detection-2.onrender.com/ws/voice-stream`
2. Send JSON: `{"user_id": "judge1"}`
3. Stream Binary Audio (Float32, 16kHz)
4. Receive Results!
