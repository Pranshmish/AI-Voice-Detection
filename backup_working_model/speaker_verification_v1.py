"""
Speaker Verification Module (Stages 3 & 4)
==========================================
Local speaker verification using SpeechBrain ECAPA-TDNN model.

Stage 3: Enrollment - Create voiceprint embeddings
Stage 4: Verification - Compare embeddings using cosine similarity
"""

import numpy as np
import json
from pathlib import Path
from typing import Tuple, Dict, Optional, List
from datetime import datetime
import logging

import config

logger = logging.getLogger(__name__)

# Fix torchaudio compatibility for newer versions (2.9+)
# SpeechBrain uses deprecated torchaudio.list_audio_backends()
import torchaudio
if not hasattr(torchaudio, 'list_audio_backends'):
    # Patch for torchaudio 2.9+ which removed this function
    torchaudio.list_audio_backends = lambda: ['soundfile']

# Lazy load SpeechBrain to avoid slow startup
_speechbrain_model = None



def get_speechbrain_model():
    """Get or initialize the SpeechBrain verification model (singleton)."""
    global _speechbrain_model
    
    if _speechbrain_model is None:
        try:
            # Fix Windows symlink issue - must be set before importing huggingface_hub
            import os
            os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
            
            # Patch huggingface_hub to not use symlinks on Windows
            import huggingface_hub
            if hasattr(huggingface_hub, 'constants'):
                huggingface_hub.constants.HF_HUB_ENABLE_HF_TRANSFER = False
            
            from speechbrain.inference.speaker import SpeakerRecognition
            
            logger.info(f"Loading SpeechBrain model: {config.SPEECHBRAIN_MODEL}")
            _speechbrain_model = SpeakerRecognition.from_hparams(
                source=config.SPEECHBRAIN_MODEL,
                savedir=str(config.MODELS_DIR / "speechbrain_ecapa"),
                run_opts={"symlink_model": False}
            )
            logger.info("SpeechBrain model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load SpeechBrain model: {e}")
            raise RuntimeError(f"SpeechBrain initialization failed: {e}")
    
    return _speechbrain_model



class VoiceprintManager:
    """
    Manages user voiceprint storage and retrieval.
    
    Stores:
    - User profiles (user_id -> metadata)
    - Embedding vectors (separate files for security)
    """
    
    def __init__(
        self,
        profiles_file: Path = config.USER_PROFILES_FILE,
        embeddings_dir: Path = config.EMBEDDINGS_DIR
    ):
        self.profiles_file = Path(profiles_file)
        self.embeddings_dir = Path(embeddings_dir)
        self._profiles = self._load_profiles()
    
    def _load_profiles(self) -> Dict:
        """Load user profiles from file."""
        if self.profiles_file.exists():
            with open(self.profiles_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_profiles(self):
        """Save user profiles to file."""
        self.profiles_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.profiles_file, 'w') as f:
            json.dump(self._profiles, f, indent=2)
    
    def save_voiceprint(
        self,
        user_id: str,
        embedding: np.ndarray,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Save a user's voiceprint embedding.
        
        Args:
            user_id: Unique user identifier
            embedding: Speaker embedding vector
            metadata: Optional enrollment metadata
            
        Returns:
            True if successful
        """
        try:
            # Save embedding as numpy file
            embedding_path = self.embeddings_dir / f"{user_id}.npy"
            np.save(embedding_path, embedding)
            
            # Update profile
            self._profiles[user_id] = {
                "user_id": user_id,
                "enrolled_at": datetime.now().isoformat(),
                "embedding_path": str(embedding_path),
                "embedding_dim": len(embedding),
                "metadata": metadata or {}
            }
            self._save_profiles()
            
            logger.info(f"Saved voiceprint for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save voiceprint: {e}")
            return False
    
    def load_voiceprint(self, user_id: str) -> Optional[np.ndarray]:
        """
        Load a user's voiceprint embedding.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Embedding array or None if not found
        """
        if user_id not in self._profiles:
            logger.warning(f"User not enrolled: {user_id}")
            return None
        
        embedding_path = Path(self._profiles[user_id]["embedding_path"])
        if not embedding_path.exists():
            logger.error(f"Embedding file missing: {embedding_path}")
            return None
        
        return np.load(embedding_path)
    
    def user_exists(self, user_id: str) -> bool:
        """Check if user is enrolled."""
        return user_id in self._profiles
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile metadata."""
        return self._profiles.get(user_id)
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user's voiceprint."""
        if user_id not in self._profiles:
            return False
        
        # Delete embedding file
        embedding_path = Path(self._profiles[user_id]["embedding_path"])
        if embedding_path.exists():
            embedding_path.unlink()
        
        # Remove from profiles
        del self._profiles[user_id]
        self._save_profiles()
        
        logger.info(f"Deleted voiceprint for user: {user_id}")
        return True
    
    def list_users(self) -> List[str]:
        """List all enrolled user IDs."""
        return list(self._profiles.keys())


class SpeakerVerifier:
    """
    Speaker verification using SpeechBrain ECAPA-TDNN.
    
    Provides enrollment and verification capabilities
    using cosine similarity between speaker embeddings.
    """
    
    def __init__(
        self,
        threshold: float = config.VERIFICATION_THRESHOLD,
        voiceprint_manager: Optional[VoiceprintManager] = None
    ):
        self.threshold = threshold
        self.voiceprint_manager = voiceprint_manager or VoiceprintManager()
        self._model = None
    
    @property
    def model(self):
        """Lazy load the SpeechBrain model."""
        if self._model is None:
            self._model = get_speechbrain_model()
        return self._model
    
    def extract_embedding(
        self,
        audio_or_path,
        sample_rate: int = config.AUDIO_SAMPLE_RATE
    ) -> np.ndarray:
        """
        Extract speaker embedding from audio.
        
        Args:
            audio_or_path: Audio array or path to audio file
            sample_rate: Sample rate of audio
            
        Returns:
            Speaker embedding vector
        """
        import torch
        import soundfile as sf
        
        if isinstance(audio_or_path, (str, Path)):
            # Load from file using soundfile (no FFmpeg required)
            audio_data, sr = sf.read(str(audio_or_path))
            
            # Resample if needed
            if sr != sample_rate:
                import librosa
                audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=sample_rate)
            
            # Convert to tensor
            waveform = torch.from_numpy(audio_data).float()
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
        else:
            # Convert numpy to tensor
            waveform = torch.from_numpy(audio_or_path).float()
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
        
        # Extract embedding
        embedding = self.model.encode_batch(waveform)
        
        # Convert to numpy and flatten
        embedding = embedding.squeeze().cpu().numpy()
        
        return embedding

    
    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Uses RAW cosine similarity for better imposter discrimination.
        ECAPA-TDNN embeddings typically have:
        - Same speaker: 0.25 - 0.70
        - Different speakers: -0.10 - 0.25
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Raw cosine similarity score (-1 to 1)
        """
        # Cosine similarity (RAW - no normalization for better discrimination)
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        similarity = dot_product / (norm1 * norm2 + 1e-8)
        
        # Return RAW cosine similarity
        # DO NOT normalize to [0,1] - this destroys discrimination!
        return float(similarity)
    
    def enroll_user(
        self,
        user_id: str,
        audio_samples: List[Path],
        overwrite: bool = False
    ) -> Tuple[bool, Dict]:
        """
        Enroll a new user with multiple audio samples.
        
        Stage 3: Speaker Enrollment
        
        Args:
            user_id: Unique user identifier
            audio_samples: List of paths to enrollment audio files
            overwrite: Whether to overwrite existing enrollment
            
        Returns:
            Tuple of (success, details)
        """
        # Check if user exists
        if self.voiceprint_manager.user_exists(user_id) and not overwrite:
            return False, {
                "status": "failed",
                "reason": f"User '{user_id}' already enrolled. Set overwrite=True to re-enroll."
            }
        
        # Validate sample count
        if len(audio_samples) < config.MIN_ENROLLMENT_SAMPLES:
            return False, {
                "status": "failed",
                "reason": f"Need at least {config.MIN_ENROLLMENT_SAMPLES} samples, got {len(audio_samples)}"
            }
        
        embeddings = []
        sample_details = []
        
        for i, audio_path in enumerate(audio_samples):
            audio_path = Path(audio_path)
            if not audio_path.exists():
                sample_details.append({
                    "sample": i + 1,
                    "path": str(audio_path),
                    "status": "failed",
                    "reason": "File not found"
                })
                continue
            
            try:
                embedding = self.extract_embedding(audio_path)
                embeddings.append(embedding)
                sample_details.append({
                    "sample": i + 1,
                    "path": str(audio_path),
                    "status": "success",
                    "embedding_dim": len(embedding)
                })
            except Exception as e:
                sample_details.append({
                    "sample": i + 1,
                    "path": str(audio_path),
                    "status": "failed",
                    "reason": str(e)
                })
        
        # Check if we have enough successful embeddings
        if len(embeddings) < config.MIN_ENROLLMENT_SAMPLES:
            return False, {
                "status": "failed",
                "reason": f"Only {len(embeddings)} valid samples, need {config.MIN_ENROLLMENT_SAMPLES}",
                "sample_details": sample_details
            }
        
        # Average embeddings to create stable voiceprint
        voiceprint = np.mean(embeddings, axis=0)
        
        # Save voiceprint
        metadata = {
            "num_samples": len(embeddings),
            "sample_details": sample_details
        }
        
        success = self.voiceprint_manager.save_voiceprint(user_id, voiceprint, metadata)
        
        if success:
            logger.info(f"Successfully enrolled user: {user_id}")
            return True, {
                "status": "success",
                "user_id": user_id,
                "num_samples_used": len(embeddings),
                "embedding_dim": len(voiceprint),
                "sample_details": sample_details
            }
        else:
            return False, {
                "status": "failed",
                "reason": "Failed to save voiceprint",
                "sample_details": sample_details
            }
    
    def verify_speaker(
        self,
        audio_or_path,
        claimed_user_id: str
    ) -> Tuple[bool, float, Dict]:
        """
        Verify if audio matches the claimed user's voiceprint.
        
        Stage 4: Speaker Verification
        
        Args:
            audio_or_path: Audio array or path to audio file
            claimed_user_id: User ID to verify against
            
        Returns:
            Tuple of (speaker_verified, similarity_score, details)
        """
        # Check if user is enrolled
        if not self.voiceprint_manager.user_exists(claimed_user_id):
            return False, 0.0, {
                "status": "failed",
                "reason": f"User '{claimed_user_id}' not enrolled"
            }
        
        # Load stored voiceprint
        stored_voiceprint = self.voiceprint_manager.load_voiceprint(claimed_user_id)
        if stored_voiceprint is None:
            return False, 0.0, {
                "status": "failed",
                "reason": "Failed to load voiceprint"
            }
        
        try:
            # Extract embedding from test audio
            test_embedding = self.extract_embedding(audio_or_path)
            
            # Compute similarity
            similarity = self.compute_similarity(test_embedding, stored_voiceprint)
            
            # Make decision
            speaker_verified = similarity >= self.threshold
            
            details = {
                "status": "success",
                "claimed_user_id": claimed_user_id,
                "similarity_score": similarity,
                "threshold": self.threshold,
                "speaker_verified": speaker_verified
            }
            
            logger.info(
                f"Verification for {claimed_user_id}: "
                f"score={similarity:.3f}, verified={speaker_verified}"
            )
            
            return speaker_verified, similarity, details
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False, 0.0, {
                "status": "failed",
                "reason": str(e)
            }
    
    def identify_speaker(
        self,
        audio_or_path,
        candidate_users: Optional[List[str]] = None
    ) -> Tuple[Optional[str], float, Dict]:
        """
        Identify the speaker from enrolled users.
        
        Args:
            audio_or_path: Audio array or path to audio file
            candidate_users: Optional list of user IDs to consider
            
        Returns:
            Tuple of (best_match_user_id, similarity_score, details)
        """
        # Get candidate users
        if candidate_users is None:
            candidate_users = self.voiceprint_manager.list_users()
        
        if not candidate_users:
            return None, 0.0, {"status": "failed", "reason": "No enrolled users"}
        
        try:
            # Extract test embedding
            test_embedding = self.extract_embedding(audio_or_path)
            
            # Compare against all candidates
            scores = {}
            for user_id in candidate_users:
                voiceprint = self.voiceprint_manager.load_voiceprint(user_id)
                if voiceprint is not None:
                    scores[user_id] = self.compute_similarity(test_embedding, voiceprint)
            
            if not scores:
                return None, 0.0, {"status": "failed", "reason": "No valid voiceprints found"}
            
            # Find best match
            best_user = max(scores, key=scores.get)
            best_score = scores[best_user]
            
            # Check if above threshold
            identified = best_score >= self.threshold
            
            details = {
                "status": "success",
                "best_match": best_user,
                "best_score": best_score,
                "threshold": self.threshold,
                "identified": identified,
                "all_scores": scores
            }
            
            return best_user if identified else None, best_score, details
            
        except Exception as e:
            logger.error(f"Identification failed: {e}")
            return None, 0.0, {"status": "failed", "reason": str(e)}


def enroll_user(user_id: str, audio_samples: List[Path]) -> Tuple[bool, Dict]:
    """Convenience function for user enrollment."""
    verifier = SpeakerVerifier()
    return verifier.enroll_user(user_id, audio_samples)


def verify_speaker(audio_path: Path, user_id: str) -> Tuple[bool, float, Dict]:
    """Convenience function for speaker verification."""
    verifier = SpeakerVerifier()
    return verifier.verify_speaker(audio_path, user_id)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("Speaker Verification Demo")
    print("=" * 50)
    
    verifier = SpeakerVerifier()
    manager = verifier.voiceprint_manager
    
    print(f"\nEnrolled users: {manager.list_users()}")
    print(f"Verification threshold: {verifier.threshold}")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "enroll" and len(sys.argv) >= 4:
            user_id = sys.argv[2]
            audio_files = [Path(f) for f in sys.argv[3:]]
            print(f"\nEnrolling user: {user_id}")
            print(f"Audio samples: {audio_files}")
            
            success, details = verifier.enroll_user(user_id, audio_files)
            print(f"Success: {success}")
            print(json.dumps(details, indent=2))
            
        elif command == "verify" and len(sys.argv) >= 4:
            user_id = sys.argv[2]
            audio_file = Path(sys.argv[3])
            print(f"\nVerifying against user: {user_id}")
            print(f"Audio: {audio_file}")
            
            verified, score, details = verifier.verify_speaker(audio_file, user_id)
            print(f"Verified: {verified}")
            print(f"Score: {score:.3f}")
            print(json.dumps(details, indent=2))
            
        elif command == "list":
            users = manager.list_users()
            print(f"\nEnrolled users: {users}")
            for user_id in users:
                profile = manager.get_user_profile(user_id)
                print(f"  {user_id}: {profile}")
                
        else:
            print("\nUsage:")
            print("  python speaker_verification.py enroll <user_id> <audio1> [audio2] ...")
            print("  python speaker_verification.py verify <user_id> <audio>")
            print("  python speaker_verification.py list")
    else:
        print("\nRun with --help for usage information")
