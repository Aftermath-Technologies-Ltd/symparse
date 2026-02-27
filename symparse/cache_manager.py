import os
import json
import hashlib
import fcntl
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".symparse_cache"

class CacheManager:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._init_metadata()

    def _init_metadata(self):
        """Ensure the global metadata file exists safely."""
        meta_file = self.cache_dir / "metadata.json"
        
        # Touch metadata file if it doesn't exist to allow read-locking later
        if not meta_file.exists():
            with open(meta_file, "a") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                if os.path.getsize(meta_file) == 0:
                    f.write(json.dumps({"schemas": {}}))
                fcntl.flock(f, fcntl.LOCK_UN)

    def _hash_schema(self, schema_dict: dict) -> str:
        """Tier 1: Deterministic exact-match hashing."""
        schema_json = json.dumps(schema_dict, sort_keys=True).encode("utf-8")
        return hashlib.sha256(schema_json).hexdigest()

    def _semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Tier 2: Fast-vector semantic similarity.
        Placeholder implementation using basic Jaccard similarity for Contrastive Collision Detection.
        Actual semantic vectors can be plugged here natively.
        """
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        if not set1 or not set2:
            return 0.0
        return len(set1.intersection(set2)) / float(len(set1.union(set2)))

    def fetch_script(self, schema_dict: dict, text: str) -> Optional[str]:
        """
        Retrieves compiled fast path logic implementing Two-Tier Caching.
        Reads must be process-safe using shared locks.
        """
        schema_hash = self._hash_schema(schema_dict)
        meta_file = self.cache_dir / "metadata.json"
        
        with open(meta_file, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH) # Shared lock for process-safe reads
            try:
                meta = json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        
        if schema_hash not in meta.get("schemas", {}):
            return None
            
        # Contrastive Collision Detection (Tier 2) check
        # We ensure the structure intended actually matches the semantic archetype of this script
        script_info = meta["schemas"][schema_hash]
        example_text = script_info.get("archetype_text", "")
        
        similarity = self._semantic_similarity(text, example_text)
        if similarity < 0.2:  # Semantic similarity threshold
            logger.warning(f"Tier 2 Collision Detected: Exact schema match but low semantic similarity ({similarity:.2f}). Bypassing script.")
            return None
            
        script_path = self.cache_dir / f"{schema_hash}.py"
        if script_path.exists():
            with open(script_path, "r") as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                try:
                    return f.read()
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
                    
        return None

    def save_script(self, schema_dict: dict, text: str, script_content: str):
        """
        Saves a generated extraction script into the cache.
        Writes must be strictly serialized via fcntl exclusive locks.
        """
        schema_hash = self._hash_schema(schema_dict)
        
        script_path = self.cache_dir / f"{schema_hash}.py"
        meta_file = self.cache_dir / "metadata.json"
        
        # Write script securely
        with open(script_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(script_content)
                f.flush()
                # Ensure data is synced to disk to avoid concurrent streaming corruption
                os.fsync(f.fileno()) 
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
                
        # Update metadata atomically via locking
        with open(meta_file, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                content = f.read()
                meta = json.loads(content) if content else {"schemas": {}}
                
                meta.setdefault("schemas", {})
                meta["schemas"][schema_hash] = {
                    "archetype_text": text,
                    "compiled": True
                }
                
                f.seek(0)
                f.truncate()
                f.write(json.dumps(meta))
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
                
    def list_cache(self):
        """Displays all locally compiled extraction scripts and schema hashes."""
        meta_file = self.cache_dir / "metadata.json"
        with open(meta_file, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                content = f.read()
                if not content:
                    return {}
                meta = json.loads(content)
                return meta.get("schemas", {})
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def clear_cache(self):
        """Wipes the local compilation directory."""
        for p in self.cache_dir.glob("*"):
            if p.is_file():
                # Acquire exclusive lock on the file before unlinking to prevent racing
                with open(p, "a") as f:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    os.unlink(p)
                    # File is unlinked, lock releases on close
