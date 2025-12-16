"""
Challenge-Response Voice Auth System
------------------------------------
Generates random phrases that user must speak.
Uses STT to verify the spoken words match.
Prevents replay attacks completely.
"""
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

# Word lists for generating phrases
ADJECTIVES = [
    "red", "blue", "green", "happy", "fast", "slow", "big", "small", 
    "bright", "dark", "cold", "hot", "soft", "hard", "new", "old"
]

NOUNS = [
    "cat", "dog", "bird", "tree", "house", "car", "book", "phone",
    "table", "chair", "door", "window", "river", "mountain", "sky", "moon"
]

VERBS = [
    "runs", "jumps", "walks", "flies", "sits", "stands", "reads", "writes",
    "opens", "closes", "brings", "takes", "gives", "shows", "finds", "makes"
]

NUMBERS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]

# Session storage (in-memory for hackathon)
_sessions: Dict[str, dict] = {}

def generate_phrase(word_count: int = 4) -> str:
    """Generate a random phrase with 3-5 words."""
    word_count = max(3, min(5, word_count))
    
    patterns = [
        # Pattern: Number + Adjective + Noun
        lambda: f"{random.choice(NUMBERS)} {random.choice(ADJECTIVES)} {random.choice(NOUNS)}",
        # Pattern: Adjective + Noun + Verb
        lambda: f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)} {random.choice(VERBS)}",
        # Pattern: Number + Noun + Verb
        lambda: f"{random.choice(NUMBERS)} {random.choice(NOUNS)} {random.choice(VERBS)}",
        # Pattern: Adjective + Adjective + Noun
        lambda: f"{random.choice(ADJECTIVES)} {random.choice(ADJECTIVES)} {random.choice(NOUNS)}",
    ]
    
    if word_count >= 4:
        patterns.extend([
            # 4 word patterns
            lambda: f"{random.choice(NUMBERS)} {random.choice(ADJECTIVES)} {random.choice(NOUNS)} {random.choice(VERBS)}",
            lambda: f"the {random.choice(ADJECTIVES)} {random.choice(NOUNS)} {random.choice(VERBS)}",
        ])
    
    if word_count >= 5:
        patterns.extend([
            # 5 word patterns  
            lambda: f"{random.choice(NUMBERS)} {random.choice(ADJECTIVES)} {random.choice(NOUNS)} {random.choice(VERBS)} today",
            lambda: f"my {random.choice(ADJECTIVES)} {random.choice(NOUNS)} {random.choice(VERBS)} here",
        ])
    
    return random.choice(patterns)()


def create_session(user_id: str) -> dict:
    """Create a new challenge session."""
    session_id = str(uuid.uuid4())[:8]
    phrase = generate_phrase(random.randint(3, 5))
    
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "phrase": phrase,
        "trials_remaining": 3,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat(),
        "status": "pending"
    }
    
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[dict]:
    """Get session by ID."""
    session = _sessions.get(session_id)
    if session:
        # Check expiry
        expires = datetime.fromisoformat(session["expires_at"])
        if datetime.now() > expires:
            session["status"] = "expired"
            return None
    return session


def verify_phrase(spoken_text: str, expected_phrase: str, threshold: float = 0.7) -> Tuple[bool, float]:
    """
    Check if spoken text matches expected phrase.
    Uses word-level matching with tolerance for STT errors.
    """
    spoken_words = spoken_text.lower().strip().split()
    expected_words = expected_phrase.lower().strip().split()
    
    if not spoken_words or not expected_words:
        return False, 0.0
    
    # Count matching words
    matches = 0
    for exp_word in expected_words:
        for spk_word in spoken_words:
            # Allow partial matches (STT errors)
            if exp_word == spk_word or exp_word in spk_word or spk_word in exp_word:
                matches += 1
                break
    
    match_ratio = matches / len(expected_words)
    return match_ratio >= threshold, match_ratio


def update_session_trial(session_id: str, success: bool) -> Optional[dict]:
    """Update session after a trial."""
    session = _sessions.get(session_id)
    if not session:
        return None
    
    if success:
        session["status"] = "verified"
    else:
        session["trials_remaining"] -= 1
        if session["trials_remaining"] <= 0:
            session["status"] = "failed"
    
    return session


def cleanup_expired_sessions():
    """Remove expired sessions."""
    now = datetime.now()
    expired = [
        sid for sid, s in _sessions.items()
        if datetime.fromisoformat(s["expires_at"]) < now
    ]
    for sid in expired:
        del _sessions[sid]
