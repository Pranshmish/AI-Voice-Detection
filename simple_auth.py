"""
Voice Auth - Sensitive Mic
==========================
- Audio boost for quiet mics
- No minimum level check
- Works with normal speaking
"""

import numpy as np
import soundfile as sf
import sounddevice as sd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from speaker_verification import SpeakerVerifier

THRESHOLD = 0.40
AUDIO_BOOST = 5.0  # Amplify audio by 5x
AUTH = SpeakerVerifier(threshold=THRESHOLD)
USER = "owner"

print("🔐 VOICE AUTH (Sensitive Mode)")
print("=" * 40)


def boost_audio(audio):
    """Boost quiet audio signal."""
    # Remove DC offset
    audio = audio - np.mean(audio)
    
    # Boost
    audio = audio * AUDIO_BOOST
    
    # Clip to prevent distortion
    audio = np.clip(audio, -1.0, 1.0)
    
    # Normalize
    max_val = np.max(np.abs(audio))
    if max_val > 0.01:
        audio = audio / max_val * 0.95
    
    return audio


def record(seconds=4):
    print(f"🎙️ Recording {seconds}s... speak normally")
    
    audio = sd.rec(int(seconds * 16000), samplerate=16000, channels=1, dtype='float32')
    sd.wait()
    audio = audio.flatten()
    
    # Show raw level
    raw_rms = np.sqrt(np.mean(audio**2))
    print(f"   Raw level: {raw_rms:.4f}")
    
    # Boost audio
    audio = boost_audio(audio)
    
    boosted_rms = np.sqrt(np.mean(audio**2))
    print(f"   Boosted:   {boosted_rms:.4f} ✅")
    
    return audio


def enroll():
    print("\n📝 ENROLLING - speak normally 3 times\n")
    
    samples = []
    for i in range(3):
        input(f"[{i+1}/3] Press Enter...")
        audio = record(4)
        f = f"_e{i}.wav"
        sf.write(f, audio, 16000)
        samples.append(f)
    
    success, _ = AUTH.enroll_user(USER, samples, overwrite=True)
    
    for f in samples:
        Path(f).unlink(missing_ok=True)
    
    print(f"\n{'✅ ENROLLED!' if success else '❌ FAILED'}")


def authenticate():
    if not AUTH.voiceprint_manager.user_exists(USER):
        print("\n❌ Not enrolled! Press 1 first.")
        return
    
    print("\n🔐 AUTHENTICATING - speak normally\n")
    input("Press Enter...")
    
    audio = record(4)
    sf.write("_auth.wav", audio, 16000)
    
    verified, score, _ = AUTH.verify_speaker("_auth.wav", USER)
    Path("_auth.wav").unlink(missing_ok=True)
    
    print(f"\n{'=' * 40}")
    print(f"Score: {score:.3f} (need {THRESHOLD})")
    print(f"{'=' * 40}")
    
    if verified:
        print("✅ OWNER - Access Granted!")
    else:
        print("❌ NOT OWNER - Access Denied!")


if __name__ == "__main__":
    enrolled = AUTH.voiceprint_manager.user_exists(USER)
    print(f"Enrolled: {'Yes' if enrolled else 'No'}")
    print(f"Boost: {AUDIO_BOOST}x\n")
    
    print("1 = Enroll")
    print("2 = Authenticate")
    print("q = Quit\n")
    
    while True:
        try:
            c = input("> ").strip()
        except:
            break
        
        if c == "1":
            enroll()
        elif c == "2":
            authenticate()
        elif c == "q":
            break
