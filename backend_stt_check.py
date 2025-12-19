
import asyncio
import websockets
import json
import numpy as np
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WS_URL = "ws://localhost:8000/ws/voice-stream"
USER_ID = "voice_owner"  # Assuming 'owner' is enrolled, or use a dummy ID

async def test_websocket_stt():
    logger.info(f"Connecting to {WS_URL}...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            logger.info("Connected!")

            # 1. Handshake
            logger.info(f"Sending handshake for user: {USER_ID}")
            await websocket.send(json.dumps({"user_id": USER_ID}))
            
            response = await websocket.recv()
            logger.info(f"Handshake response: {response}")
            
            # 2. Prepare Dummy Audio (Silence + Sine Wave)
            # 16kHz sample rate, 1 second of audio
            sample_rate = 16000
            duration = 1.0 
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            
            # Generate a 440Hz sine wave (simulating sound)
            # It won't transcribe to meaningful text usually, but it should trigger VAD
            audio_data = 0.5 * np.sin(2 * np.pi * 440 * t) 
            
            # Append 1s of silence to trigger VAD segment finalization
            silence = np.zeros(int(sample_rate * 1.0), dtype=np.float32)
            audio_data = np.concatenate((audio_data, silence))
            
            audio_data = audio_data.astype(np.float32)
            
            # 3. Send Audio Chunks
            chunk_size = 2048
            logger.info("Sending audio chunks...")
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i+chunk_size]
                if len(chunk) < chunk_size:
                    padding = np.zeros(chunk_size - len(chunk), dtype=np.float32)
                    chunk = np.concatenate((chunk, padding))
                
                await websocket.send(chunk.tobytes())
                await asyncio.sleep(0.01) # Simulate real-time streaming
                
                # Check for responses occasionally
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.001)
                    data = json.loads(response)
                    logger.info(f"Received: {data}")
                    if data.get("type") == "result":
                        logger.info("✅ SUCCESS: Received STT result!")
                        # We don't expect accurate text from a sine wave, but we expect a result
                        return
                    
                except asyncio.TimeoutError:
                    pass
            
            # Wait a bit for final processing
            logger.info("Finished sending audio. Waiting for response...")
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    logger.info(f"Received: {data}")
                    if data.get("type") == "result":
                         logger.info("✅ SUCCESS: Received STT result!")
                         return
            except asyncio.TimeoutError:
                logger.error("❌ TIMEOUT: No result received after finishing audio.")

    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket_stt())
    except KeyboardInterrupt:
        pass
