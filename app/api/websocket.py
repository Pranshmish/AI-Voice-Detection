"""
WebSocket Streaming - FAST MODE for Continuous Auth
Optimized for seamless voice command verification
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import numpy as np
import logging
import json
import asyncio
import time
from app.core.inference import authenticate_voice

router = APIRouter(tags=["Voice Streaming"])

# Optimized Constants for Fast Continuous Auth
SAMPLE_RATE = 16000
CHUNK_MS = 128  # Smaller chunks for lower latency (2048 samples at 16kHz)
VAD_THRESHOLD = 0.008  # Lower threshold for more sensitivity
SILENCE_DURATION_MS = 250  # Faster cutoff
MAX_SPEECH_DURATION_S = 2.5  # Shorter max for quick verification
MIN_SPEECH_DURATION_S = 0.4  # Minimum to avoid noise triggers

class AudioBuffer:
    """Fast VAD-based audio buffer for real-time voice verification"""
    def __init__(self):
        self.buffer, self.speech_chunks = [], []
        self.is_speaking = False
        self.silence_chunks = 0
        self.silence_limit = int(SILENCE_DURATION_MS / CHUNK_MS)

    def add_chunk(self, chunk: np.ndarray) -> np.ndarray:
        energy = np.sqrt(np.mean(chunk**2))
        if energy > VAD_THRESHOLD:
            if not self.is_speaking:
                self.is_speaking = True
                self.speech_chunks = []
            self.speech_chunks.append(chunk)
            self.silence_chunks = 0
            # Quick cutoff at max duration
            if len(self.speech_chunks) * CHUNK_MS / 1000 > MAX_SPEECH_DURATION_S:
                segment = np.concatenate(self.speech_chunks)
                self.reset()
                return segment
        elif self.is_speaking:
            self.silence_chunks += 1
            self.speech_chunks.append(chunk) 
            if self.silence_chunks >= self.silence_limit:
                full_segment = np.concatenate(self.speech_chunks[:-self.silence_limit])
                self.reset()
                # Require minimum duration
                if len(full_segment) / SAMPLE_RATE < MIN_SPEECH_DURATION_S:
                    return None
                return full_segment
        return None

    def reset(self):
        self.is_speaking, self.speech_chunks, self.silence_chunks = False, [], 0

@router.websocket("/ws/voice-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WS: Connected")
    
    try:
        # 1. Simple Handshake (No Key needed)
        data = await websocket.receive_text()
        msg = json.loads(data)
        user_id = msg.get("user_id")
        
        # Ack
        await websocket.send_json({"type": "status", "status": "listening"})

        buffer = AudioBuffer()
        while True:
            data = await websocket.receive_bytes()
            audio_chunk = np.frombuffer(data, dtype=np.float32)
            segment = buffer.add_chunk(audio_chunk)
            
            if segment is not None:
                await websocket.send_json({"type": "status", "status": "verifying"})
                t0 = time.time()
                is_auth, score, decision = await asyncio.to_thread(authenticate_voice, segment, user_id)
                latency = round((time.time() - t0) * 1000, 2)
                await websocket.send_json({
                    "type": "result",
                    "authorized": is_auth,
                    "score": round(score, 3),
                    "decision": decision,
                    "latency_ms": latency
                })
                await websocket.send_json({"type": "status", "status": "listening"})

    except WebSocketDisconnect: pass
    except Exception: pass
