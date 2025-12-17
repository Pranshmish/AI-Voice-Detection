"""
Voice Auth - Sensitive Mic + Phrase Verification
=================================================
- Audio boost for quiet mics
- No minimum level check
- Works with normal speaking
- Challenge-response phrase verification (anti-replay)
"""

import numpy as np
import soundfile as sf
import sounddevice as sd
from pathlib import Path
import random
import warnings
warnings.filterwarnings('ignore')

from speaker_verification import SpeakerVerifier

# ========================================
# CONFIGURATION (ECAPA-TDNN Calibrated)
# ========================================
# Thresholds based on ECAPA-TDNN cosine similarity ranges:
#   >= 0.75: High confidence auth
#   0.65-0.75: Borderline (require second challenge)
#   < 0.65: Likely imposter
THRESHOLD_HIGH = 0.75  # High confidence owner
THRESHOLD_BORDERLINE = 0.65  # Borderline - needs second challenge
THRESHOLD_IMPOSTER = 0.45  # Definitely not owner
THRESHOLD = 0.65  # Main threshold for SpeakerVerifier

PHRASE_MATCH_THRESHOLD = 0.80  # 80% word overlap required
FORCE_REENROLL = False  # Set True to force fresh enrollment
MIN_ENROLLMENT_SAMPLES = 3  # 3 samples for quick enrollment

AUTH = SpeakerVerifier(threshold=THRESHOLD)
USER = "owner"

# ========================================
# PHRASE GENERATION (5-8 words for security)
# ========================================
# Avoid simple patterns, use natural phrases
PHRASE_TEMPLATES = [
    "the {adj} {noun} {verb} very {adv}",
    "my {adj} {noun} is {adj} today",
    "please {verb} the {adj} {noun} now",
    "{num} {adj} {noun}s {verb} {adv}",
    "I can see a {adj} {noun} {verb}",
]

ADJECTIVES = ["red", "blue", "green", "big", "small", "happy", "quiet", "bright"]
NOUNS = ["cat", "dog", "bird", "tree", "house", "book", "car", "table"]
VERBS = ["runs", "jumps", "walks", "sits", "reads", "opens", "moves", "stays"]
ADVERBS = ["quickly", "slowly", "softly", "loudly", "gently"]
NUMBERS = ["two", "three", "four", "five", "seven"]


def generate_phrase() -> str:
    """Generate a random 5-8 word phrase."""
    template = random.choice(PHRASE_TEMPLATES)
    phrase = template.format(
        adj=random.choice(ADJECTIVES),
        noun=random.choice(NOUNS),
        verb=random.choice(VERBS),
        adv=random.choice(ADVERBS),
        num=random.choice(NUMBERS)
    )
    return phrase


# ========================================
# LOCAL STT (OpenAI Whisper - Best Free STT)
# ========================================
_whisper_model = None
_whisper_available = False


def _load_whisper():
    """Load OpenAI Whisper model for high-quality STT."""
    global _whisper_model, _whisper_available
    
    try:
        import whisper
        
        # Use 'small' model for BEST accuracy (larger = more accurate)
        # Options: tiny (fast, less accurate), base, small (recommended), medium, large
        model_name = "small"  # UPGRADED for better accuracy
        print(f"📦 Loading Whisper '{model_name}' model (high accuracy)...")
        print("   (First load may download ~500MB model)")
        _whisper_model = whisper.load_model(model_name)
        _whisper_available = True
        print("✅ Whisper STT loaded!")
        
    except ImportError:
        print("⚠️ Whisper not installed. Run: pip install openai-whisper")
        _whisper_available = False
    except Exception as e:
        print(f"⚠️ Whisper load failed: {e}")
        # Try tiny model as fallback
        try:
            import whisper
            print("📦 Trying 'tiny' model as fallback...")
            _whisper_model = whisper.load_model("tiny")
            _whisper_available = True
            print("✅ Whisper (tiny) loaded!")
        except:
            _whisper_available = False


def transcribe_audio(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """Convert audio to text using OpenAI Whisper."""
    global _whisper_model, _whisper_available
    
    if _whisper_model is None:
        _load_whisper()
    
    if not _whisper_available or _whisper_model is None:
        return ""
    
    try:
        import whisper
        
        # Whisper expects float32 audio normalized to [-1, 1]
        # and at 16kHz sample rate
        audio_float = audio.astype(np.float32)
        
        # Pad/trim to 30 seconds (Whisper's expected input)
        audio_padded = whisper.pad_or_trim(audio_float)
        
        # Create mel spectrogram
        mel = whisper.log_mel_spectrogram(audio_padded).to(_whisper_model.device)
        
        # Decode
        options = whisper.DecodingOptions(
            language="en",
            without_timestamps=True,
            fp16=False  # Use FP32 for CPU compatibility
        )
        result = whisper.decode(_whisper_model, mel, options)
        
        text = result.text.strip()
        return text
        
    except Exception as e:
        print(f"❌ STT error: {e}")
        return ""


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def verify_phrase(spoken_text: str, expected_phrase: str) -> tuple:
    """
    Phrase verification with fuzzy matching.
    Returns (status, score) where status is 'ok', 'borderline', or 'fail'
    """
    import re
    
    # Normalize
    spoken_clean = re.sub(r'[^a-z0-9\s]', '', spoken_text.lower().strip())
    expected_clean = re.sub(r'[^a-z0-9\s]', '', expected_phrase.lower().strip())
    
    spoken_words = spoken_clean.split()
    expected_words = expected_clean.split()
    
    print(f"   [STT] Expected: {expected_words}")
    print(f"   [STT] Spoken:   {spoken_words}")
    
    if not expected_words:
        return 'fail', 0.0
    if not spoken_words:
        return 'fail', 0.0
    
    # Method 1: Word overlap ratio
    matches = sum(1 for w in expected_words if w in spoken_words)
    word_overlap = matches / len(expected_words)
    
    # Method 2: Normalized Levenshtein distance
    lev_dist = levenshtein_distance(spoken_clean, expected_clean)
    max_len = max(len(spoken_clean), len(expected_clean))
    lev_normalized = lev_dist / max_len if max_len > 0 else 1.0
    
    print(f"   [STT] Word overlap: {word_overlap:.1%} ({matches}/{len(expected_words)})")
    print(f"   [STT] Levenshtein: {lev_normalized:.2f} (lower=better)")
    
    # Decision logic
    if word_overlap >= 0.8 or lev_normalized <= 0.3:
        return 'ok', word_overlap
    elif word_overlap >= 0.6:
        return 'borderline', word_overlap
    else:
        return 'fail', word_overlap


print("🔐 VOICE AUTH (Sensitive Mode + Phrase)")
print("=" * 45)


def boost_audio(audio, verbose=False):
    """Normalize audio with auto-gain for consistent levels."""
    # Remove DC offset
    audio = audio - np.mean(audio)
    
    # Check current level
    current_rms = np.sqrt(np.mean(audio**2))
    
    # Auto-gain: normalize to target RMS of 0.20
    target_rms = 0.20
    if current_rms > 0.001:
        auto_gain = target_rms / current_rms
        # Limit auto-gain to prevent noise amplification
        auto_gain = min(auto_gain, 30.0)
        audio = audio * auto_gain
        if verbose:
            print(f"   Auto-gain: {auto_gain:.1f}x")
    
    # Clip to prevent distortion
    audio = np.clip(audio, -1.0, 1.0)
    
    # Final normalize to 95%
    max_val = np.max(np.abs(audio))
    if max_val > 0.01:
        audio = audio / max_val * 0.95
    
    return audio


def record(seconds=4, show_levels=True):
    """Record audio from microphone."""
    print(f"🎙️ Recording {seconds}s... speak normally")
    
    audio = sd.rec(int(seconds * 16000), samplerate=16000, channels=1, dtype='float32')
    sd.wait()
    audio = audio.flatten()
    
    # Show raw level
    raw_rms = np.sqrt(np.mean(audio**2))
    if show_levels:
        print(f"   Raw level: {raw_rms:.4f}")
    
    # Boost audio
    audio = boost_audio(audio, verbose=show_levels)
    
    boosted_rms = np.sqrt(np.mean(audio**2))
    if show_levels:
        print(f"   Boosted:   {boosted_rms:.4f} ✅")
    
    return audio


def enroll():
    """Enroll user with 5 voice samples for robust verification."""
    ENROLL_PHRASE = "my voice is my password please verify me now"
    
    print(f"\n📝 ENROLLING - say the phrase {MIN_ENROLLMENT_SAMPLES} times\n")
    print("=" * 55)
    print(f"📢 SAY THIS PHRASE: \"{ENROLL_PHRASE}\"")
    print("=" * 55)
    print("(Speak in a quiet room, normal volume)\n")
    
    samples = []
    for i in range(MIN_ENROLLMENT_SAMPLES):
        input(f"[{i+1}/{MIN_ENROLLMENT_SAMPLES}] Press Enter when ready...")
        print(f"   Say: \"{ENROLL_PHRASE}\"")
        audio = record(4)  # 4 seconds for phrase
        
        # Show STT result
        print("   Transcribing...")
        spoken = transcribe_audio(audio)
        print(f"   📝 STT: \"{spoken}\"")
        
        f = f"_e{i}.wav"
        sf.write(f, audio, 16000)
        samples.append(f)
        print(f"   ✅ Sample {i+1}/{MIN_ENROLLMENT_SAMPLES} recorded\n")
    
    print("Processing enrollment...")
    success, details = AUTH.enroll_user(USER, samples, overwrite=True)
    
    for f in samples:
        Path(f).unlink(missing_ok=True)
    
    if success:
        print("\n" + "=" * 55)
        print("✅ ENROLLED SUCCESSFULLY!")
        print(f"   Samples used: {MIN_ENROLLMENT_SAMPLES}")
        print(f"   Enrollment phrase: \"{ENROLL_PHRASE}\"")
        print("=" * 55)
    else:
        print(f"\n❌ ENROLLMENT FAILED: {details}")


def authenticate_basic():
    """Basic authentication - voice only."""
    if not AUTH.voiceprint_manager.user_exists(USER):
        print("\n❌ Not enrolled! Press 1 first.")
        return
    
    print("\n🔐 BASIC AUTH - speak normally\n")
    input("Press Enter...")
    
    audio = record(4)
    sf.write("_auth.wav", audio, 16000)
    
    verified, score, _ = AUTH.verify_speaker("_auth.wav", USER)
    Path("_auth.wav").unlink(missing_ok=True)
    
    print(f"\n{'=' * 45}")
    print(f"Voice Score: {score:.3f} (need {THRESHOLD})")
    print(f"{'=' * 45}")
    
    if verified:
        print("✅ OWNER - Access Granted!")
    else:
        print("❌ NOT OWNER - Access Denied!")


def authenticate_with_phrase():
    """Challenge-response authentication with proper decision bands."""
    if not AUTH.voiceprint_manager.user_exists(USER):
        print("\n❌ Not enrolled! Press 1 first.")
        return
    
    phrase = generate_phrase()
    
    print("\n🔐 CHALLENGE AUTH - voice + phrase verification\n")
    print(f"{'=' * 55}")
    print(f"📢 SAY THIS PHRASE: \"{phrase}\"")
    print(f"{'=' * 55}")
    print()
    
    input("Press Enter when ready to speak...")
    
    audio = record(4)  # 4 seconds
    sf.write("_auth.wav", audio, 16000)
    
    # 1. Voice verification
    print("\n🔍 Verifying voice (ECAPA-TDNN)...")
    _, voice_score, _ = AUTH.verify_speaker("_auth.wav", USER)
    
    # 2. Phrase verification  
    print("🔍 Verifying phrase (Whisper STT)...")
    spoken_text = transcribe_audio(audio)
    phrase_status, phrase_score = verify_phrase(spoken_text, phrase)
    
    Path("_auth.wav").unlink(missing_ok=True)
    
    # Results
    print(f"\n{'=' * 55}")
    print(f"🗣️ You said: \"{spoken_text}\"")
    print(f"📋 Expected: \"{phrase}\"")
    print(f"{'=' * 55}")
    
    # Voice score band
    if voice_score >= THRESHOLD_HIGH:
        voice_band = "HIGH ✅"
    elif voice_score >= THRESHOLD_BORDERLINE:
        voice_band = "BORDERLINE ⚠️"
    else:
        voice_band = "LOW ❌"
    
    print(f"Voice Score:  {voice_score:.3f} [{voice_band}]")
    print(f"   (High >= {THRESHOLD_HIGH}, Borderline >= {THRESHOLD_BORDERLINE})")
    print(f"Phrase Status: {phrase_status.upper()} (overlap: {phrase_score:.0%})")
    print(f"{'=' * 55}")
    
    # Decision logic per spec
    if phrase_status == 'fail':
        print("❌ DENIED - Wrong phrase spoken!")
    elif voice_score >= THRESHOLD_HIGH and phrase_status == 'ok':
        print("✅ OWNER VERIFIED (High Confidence) - Access Granted!")
    elif voice_score >= THRESHOLD_BORDERLINE and phrase_status == 'ok':
        print("✅ OWNER VERIFIED (Medium Confidence) - Access Granted!")
    elif voice_score >= THRESHOLD_BORDERLINE and phrase_status == 'borderline':
        print("⚠️ BORDERLINE - Please try again with a new phrase.")
    elif voice_score < THRESHOLD_BORDERLINE:
        print("❌ DENIED - Voice does not match (likely impostor)!")
    else:
        print("⚠️ UNCERTAIN - Additional verification needed.")


def test_stt():
    """Test STT only - no authentication."""
    print("\n🎤 STT TEST - speak anything\n")
    input("Press Enter...")
    
    audio = record(5)
    text = transcribe_audio(audio)
    
    print(f"\n{'=' * 45}")
    print(f"🗣️ Recognized: \"{text}\"")
    print(f"{'=' * 45}")


if __name__ == "__main__":
    # Initialize Whisper on startup
    _load_whisper()
    
    # Force re-enrollment if flag is set
    if FORCE_REENROLL and AUTH.voiceprint_manager.user_exists(USER):
        print("\n⚠️ FORCE RE-ENROLL enabled - deleting old voiceprint...")
        AUTH.voiceprint_manager.delete_user(USER)
        print("✅ Old voiceprint deleted. Please enroll again.\n")
    
    enrolled = AUTH.voiceprint_manager.user_exists(USER)
    print(f"Enrolled: {'Yes ✅' if enrolled else 'No ❌ (Press 1 to enroll)'}")
    print(f"Voice Thresholds: High={THRESHOLD_HIGH}, Borderline={THRESHOLD_BORDERLINE}")
    print(f"Phrase Match: {PHRASE_MATCH_THRESHOLD:.0%} required\n")
    
    print("1 = Enroll")
    print("2 = Basic Auth (voice only)")
    print("3 = Challenge Auth (voice + phrase) ⭐")
    print("4 = Test STT")
    print("q = Quit\n")
    
    while True:
        try:
            c = input("> ").strip()
        except:
            break
        
        if c == "1":
            enroll()
        elif c == "2":
            authenticate_basic()
        elif c == "3":
            authenticate_with_phrase()
        elif c == "4":
            test_stt()
        elif c == "q":
            break
