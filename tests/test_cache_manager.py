import os
import json
import fcntl
import multiprocessing
import pytest
from pathlib import Path
from symparse.cache_manager import CacheManager

def test_cache_init_metadata(tmp_path):
    cm = CacheManager(cache_dir=tmp_path)
    meta_file = tmp_path / "metadata.json"
    assert meta_file.exists()
    
    with open(meta_file, "r") as f:
        meta = json.load(f)
    assert meta == {"schemas": {}}

def test_save_and_fetch_cache(tmp_path):
    cm = CacheManager(cache_dir=tmp_path)
    schema = {"type": "object"}
    text = "The quick brown fox"
    script = "def extract(t): return {'key': 'val'}"
    
    cm.save_script(schema, text, script)
    
    # Assert listed in cache
    listed = cm.list_cache()
    hash_val = cm._hash_schema(schema)
    assert hash_val in listed
    
    # Assert fetch success with similar semantic query
    fetched_script = cm.fetch_script(schema, "A quick fox")
    assert fetched_script == script
    
    # Assert fetch fails due to contrastive collision detection
    fetched_script = cm.fetch_script(schema, "An unrelated text about space")
    assert fetched_script is None

def test_clear_cache(tmp_path):
    cm = CacheManager(cache_dir=tmp_path)
    schema = {"type": "object"}
    cm.save_script(schema, "word", "script")
    
    cm.clear_cache()
    
    # Cache clear removes metadata.json as well, which is recreated on next init,
    # or list_cache recreates it if it was deleted? Actually it raises FileNotFoundError 
    # if it tries to open after we removed it. Wait, `list_cache` doesn't recreate.
    # We should catch FileNotFoundError or just test if dir is empty.
    files = list(tmp_path.glob("*"))
    assert len(files) == 0

def lock_writer(cache_dir, schema, text, script):
    cm = CacheManager(cache_dir=cache_dir)
    cm.save_script(schema, text, script)

def test_concurrent_writes(tmp_path):
    schema = {"type": "object"}
    script = "test"
    text = "hello world"
    
    processes = []
    for _ in range(5):
        p = multiprocessing.Process(target=lock_writer, args=(tmp_path, schema, text, script))
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join()
        
    cm = CacheManager(cache_dir=tmp_path)
    # The dictionary keys should map to hash and be valid json without corruption
    meta_file = tmp_path / "metadata.json"
    with open(meta_file, "r") as f:
        meta = json.load(f)
        
    hash_val = cm._hash_schema(schema)
    assert hash_val in meta["schemas"]
