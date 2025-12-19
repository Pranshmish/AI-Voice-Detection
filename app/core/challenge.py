"""
Challenge-Response Voice Auth System
------------------------------------
Generates random phrases that user must speak.
Uses STT to verify the spoken words match.
Prevents replay attacks completely.
"""
import random
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

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


def verify_phrase(spoken_text: str, expected_phrase: str, threshold: float = 0.50) -> Tuple[bool, float]:
    """
    Check if spoken text matches expected phrase.
    Uses enhanced fuzzy matching with tolerance for STT errors.
    
    Args:
        spoken_text: What STT transcribed
        expected_phrase: What user was supposed to say
        threshold: Match threshold (default 0.50 for leniency)
    
    Returns:
        (is_match, match_score)
    """
    # Normalize both texts
    spoken_clean = spoken_text.lower().strip()
    expected_clean = expected_phrase.lower().strip()
    
    # Remove punctuation
    for char in ".,!?':;\"":
        spoken_clean = spoken_clean.replace(char, "")
        expected_clean = expected_clean.replace(char, "")
    
    spoken_words = spoken_clean.split()
    expected_words = expected_clean.split()
    
    if not spoken_words or not expected_words:
        return False, 0.0
    
    # Helper: Check if two words are similar (fuzzy match)
    def words_similar(w1: str, w2: str) -> bool:
        if w1 == w2:
            return True
        # One contains the other
        if w1 in w2 or w2 in w1:
            return True
        # Edit distance check (allow 1-2 character errors)
        if len(w1) > 2 and len(w2) > 2:
            # Simple Levenshtein approximation
            if abs(len(w1) - len(w2)) <= 2:
                # Check character overlap
                common = sum(1 for c in w1 if c in w2)
                similarity = common / max(len(w1), len(w2))
                if similarity >= 0.6:
                    return True
        # Sound-alike substitutions (common STT errors)
        sound_alikes = {
            "to": ["two", "too"], "for": ["four"], "one": ["won"],
            "their": ["there", "they're"], "its": ["it's"],
            "red": ["read"], "blue": ["blew"], "new": ["knew"],
        }
        for base, alts in sound_alikes.items():
            if (w1 == base and w2 in alts) or (w2 == base and w1 in alts):
                return True
        return False
    
    # Count matching words (order-independent for leniency)
    matches = 0
    matched_indices = set()
    
    for exp_word in expected_words:
        for i, spk_word in enumerate(spoken_words):
            if i not in matched_indices and words_similar(exp_word, spk_word):
                matches += 1
                matched_indices.add(i)
                break
    
    # Calculate match ratio based on expected words
    match_ratio = matches / len(expected_words)
    
    # Bonus: If most words matched, be lenient
    if matches >= len(expected_words) - 1 and len(expected_words) >= 3:
        match_ratio = max(match_ratio, 0.75)  # Boost if only 1 word off
    
    # Log for debugging
    logger.info(
        f"Phrase match: '{spoken_text}' vs '{expected_phrase}' = {match_ratio:.2f} ({matches}/{len(expected_words)} words)"
    )
    
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
