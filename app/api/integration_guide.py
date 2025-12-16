"""
Integration Guide API
---------------------
Returns JSON documentation for frontend integration.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Documentation"])

INTEGRATION_GUIDE = {
    "api_name": "Voice Authentication API",
    "version": "1.0.0",
    "base_url": "https://your-app.onrender.com",
    
    "quick_start": {
        "step_1": "Enroll user with 3+ voice samples",
        "step_2": "Start challenge session to get random phrase",
        "step_3": "User speaks the phrase, send audio to verify",
        "step_4": "Check both speaker_match and phrase_match for security"
    },
    
    "endpoints": {
        "health": {
            "method": "GET",
            "url": "/api/v1/voice/health",
            "description": "Check if API and model are ready",
            "response": {
                "status": "ready_for_demo",
                "model_loaded": True
            }
        },
        
        "enroll": {
            "method": "POST",
            "url": "/api/v1/voice/enroll",
            "description": "Enroll a new user with voice samples",
            "content_type": "multipart/form-data",
            "parameters": {
                "audio_files": "3+ WAV/MP3 files (required)",
                "user_id": "string - unique user identifier (required)",
                "overwrite": "boolean - overwrite existing (default: true)"
            },
            "frontend_code": """
const enrollUser = async (userId, audioFiles) => {
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('overwrite', 'true');
    audioFiles.forEach(file => formData.append('audio_files', file));
    
    const response = await fetch('/api/v1/voice/enroll', {
        method: 'POST',
        body: formData
    });
    return response.json();
};
""",
            "response": {
                "success": True,
                "user_id": "user123",
                "message": "User 'user123' enrolled successfully"
            }
        },
        
        "authenticate": {
            "method": "POST",
            "url": "/api/v1/voice/authenticate",
            "description": "Simple voice authentication (no challenge)",
            "content_type": "multipart/form-data",
            "parameters": {
                "audio": "WAV/MP3 file (required)",
                "user_id": "string (required)",
                "session_id": "string (optional)"
            },
            "frontend_code": """
const authenticate = async (userId, audioBlob) => {
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('audio', audioBlob, 'recording.wav');
    
    const response = await fetch('/api/v1/voice/authenticate', {
        method: 'POST',
        body: formData
    });
    return response.json();
};
""",
            "response": {
                "authenticated": True,
                "confidence_score": 0.85,
                "decision": "AUTHENTIC",
                "message": "Authenticated"
            }
        },
        
        "challenge_start": {
            "method": "POST",
            "url": "/api/v1/challenge/start",
            "description": "Start challenge-response auth (RECOMMENDED - prevents replay attacks)",
            "content_type": "multipart/form-data",
            "parameters": {
                "user_id": "string (required)"
            },
            "frontend_code": """
const startChallenge = async (userId) => {
    const formData = new FormData();
    formData.append('user_id', userId);
    
    const response = await fetch('/api/v1/challenge/start', {
        method: 'POST',
        body: formData
    });
    const data = await response.json();
    
    // Display phrase to user
    showPhrase(data.phrase);  // e.g., "five red birds"
    
    return data;
};
""",
            "response": {
                "session_id": "a1b2c3d4",
                "phrase": "five red birds",
                "trials_remaining": 3,
                "expires_in_seconds": 300,
                "stt_available": True
            }
        },
        
        "challenge_verify": {
            "method": "POST",
            "url": "/api/v1/challenge/verify",
            "description": "Verify user spoke the correct phrase with correct voice",
            "content_type": "multipart/form-data",
            "parameters": {
                "session_id": "string from challenge/start (required)",
                "audio": "WAV/MP3 file of user speaking phrase (required)"
            },
            "frontend_code": """
const verifyChallenge = async (sessionId, audioBlob) => {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('audio', audioBlob, 'challenge.wav');
    
    const response = await fetch('/api/v1/challenge/verify', {
        method: 'POST',
        body: formData
    });
    const data = await response.json();
    
    if (data.success) {
        // Both voice AND phrase matched!
        grantAccess();
    } else if (data.trials_remaining > 0) {
        // Allow retry
        showError(data.message);
    } else {
        // All trials used
        lockout();
    }
    
    return data;
};
""",
            "response": {
                "success": True,
                "speaker_match": True,
                "phrase_match": True,
                "spoken_text": "five red birds",
                "expected_phrase": "five red birds",
                "speaker_score": 0.85,
                "phrase_score": 1.0,
                "trials_remaining": 2,
                "message": "✅ Verified! Voice + Phrase matched."
            }
        },
        
        "websocket_stream": {
            "url": "wss://your-app.onrender.com/ws/voice-stream",
            "description": "Real-time voice streaming for continuous auth",
            "protocol": "WebSocket",
            "handshake": {
                "send": {"user_id": "user123"},
                "receive": {"type": "status", "status": "listening"}
            },
            "streaming": {
                "send": "Raw audio bytes (float32, 16kHz, mono)",
                "receive": {
                    "type": "result",
                    "authorized": True,
                    "score": 0.85,
                    "decision": "AUTHENTIC",
                    "latency_ms": 150
                }
            },
            "frontend_code": """
const connectVoiceStream = (userId) => {
    const ws = new WebSocket('wss://your-app.onrender.com/ws/voice-stream');
    
    ws.onopen = () => {
        ws.send(JSON.stringify({ user_id: userId }));
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'result') {
            console.log('Auth result:', data.authorized, data.score);
        }
    };
    
    // Stream audio from microphone
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            const audioContext = new AudioContext({ sampleRate: 16000 });
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            processor.onaudioprocess = (e) => {
                const samples = e.inputBuffer.getChannelData(0);
                ws.send(new Float32Array(samples).buffer);
            };
            
            source.connect(processor);
            processor.connect(audioContext.destination);
        });
    
    return ws;
};
"""
        }
    },
    
    "complete_flow_example": """
// Complete Challenge-Response Flow (Recommended)

async function secureVoiceAuth(userId) {
    // Step 1: Start challenge
    const challenge = await startChallenge(userId);
    
    // Step 2: Show phrase to user
    displayMessage(`Please say: "${challenge.phrase}"`);
    
    // Step 3: Record user speaking
    const audioBlob = await recordAudio(3);  // 3 seconds
    
    // Step 4: Verify
    const result = await verifyChallenge(challenge.session_id, audioBlob);
    
    if (result.success) {
        // SUCCESS! Both voice identity AND phrase matched
        return { authenticated: true, score: result.speaker_score };
    } else {
        return { 
            authenticated: false, 
            message: result.message,
            trialsLeft: result.trials_remaining 
        };
    }
}

// Helper: Record audio
function recordAudio(durationSec) {
    return new Promise(async (resolve) => {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        const chunks = [];
        
        recorder.ondataavailable = (e) => chunks.push(e.data);
        recorder.onstop = () => {
            const blob = new Blob(chunks, { type: 'audio/wav' });
            stream.getTracks().forEach(t => t.stop());
            resolve(blob);
        };
        
        recorder.start();
        setTimeout(() => recorder.stop(), durationSec * 1000);
    });
}
""",
    
    "audio_requirements": {
        "format": ["WAV", "MP3", "OGG", "FLAC"],
        "sample_rate": "16000 Hz (recommended)",
        "channels": "Mono",
        "duration": "2-10 seconds per sample",
        "tips": [
            "Ensure clear audio without background noise",
            "Speak in normal conversational tone",
            "For enrollment, use 3-5 different phrases"
        ]
    },
    
    "security_notes": {
        "challenge_response": "Always use /challenge/* endpoints for production - prevents replay attacks",
        "replay_attacks": "Random phrases ensure recordings cannot be reused",
        "api_key": "Currently open for hackathon - add API key auth for production"
    }
}


@router.get("/integration")
async def get_integration_guide():
    """Get complete frontend integration guide as JSON."""
    return JSONResponse(content=INTEGRATION_GUIDE)


@router.get("/integration/endpoints")
async def get_endpoints_only():
    """Get just the endpoint definitions."""
    return JSONResponse(content=INTEGRATION_GUIDE["endpoints"])


@router.get("/integration/example")
async def get_example_code():
    """Get complete flow example code."""
    return JSONResponse(content={
        "complete_flow": INTEGRATION_GUIDE["complete_flow_example"],
        "audio_requirements": INTEGRATION_GUIDE["audio_requirements"]
    })
