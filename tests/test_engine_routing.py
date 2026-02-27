import pytest
import os
import json
from unittest.mock import patch
from symparse.engine import process_stream, EngineFailure, GracefulDegradationMode
from symparse.validator import SchemaViolationError
from symparse.cache_manager import CacheManager

def test_process_stream_fast_path(monkeypatch, tmp_path):
    schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
    text = "My name is Alice"
    
    # Pre-populate cache
    cm = CacheManager(cache_dir=tmp_path)
    script = json.dumps({"name": "name is (.*?)$"})
    cm.save_script(schema, text, script)
    
    # Mock AI Client to fail if it gets called (proves Fast Path worked)
    class MockAIClient:
        def extract(self, *args, **kwargs):
            raise Exception("AI should not be called")
            
    monkeypatch.setattr('symparse.engine.AIClient', MockAIClient)
    monkeypatch.setattr('symparse.engine.CacheManager', lambda: cm)
    
    # Extract via Fast Path
    result = process_stream(text, schema)
    assert result == {"name": "Alice"}
    
def test_process_stream_fast_path_fallback(monkeypatch, tmp_path):
    schema = {"type": "object", "properties": {"age": {"type": "integer"}}, "required": ["age"]}
    text = "I am 30 years old"
    
    # Pre-populate cache with script that extracts string instead of int to trigger validation failure
    cm = CacheManager(cache_dir=tmp_path)
    script = json.dumps({"age": "am (.*?) years"})
    cm.save_script(schema, text, script)
    
    # Mock AI Client to succeed after fallback
    class MockAIClient:
        def extract(self, *args, **kwargs):
            return {"age": 30}
            
    monkeypatch.setattr('symparse.engine.AIClient', MockAIClient)
    monkeypatch.setattr('symparse.engine.CacheManager', lambda: cm)
    
    result = process_stream(text, schema)
    assert result == {"age": 30}
    
    # Assert cache is purged
    assert cm.fetch_script(schema, text) is None

def test_process_stream_compile(monkeypatch, tmp_path):
    schema = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    text = "ID: 1234"
    
    class MockAIClient:
        def extract(self, *args, **kwargs):
            return {"id": "1234"}
            
    monkeypatch.setattr('symparse.engine.AIClient', MockAIClient)
    
    def mock_generate_script(*args, **kwargs):
        return json.dumps({"id": "ID: (\\d+)"})
        
    monkeypatch.setattr('symparse.engine.generate_script', mock_generate_script)
    
    cm = CacheManager(cache_dir=tmp_path)
    monkeypatch.setattr('symparse.engine.CacheManager', lambda: cm)
    
    # Run with compile
    result = process_stream(text, schema, compile=True)
    assert result == {"id": "1234"}
    
    # Verify cache has it
    script = cm.fetch_script(schema, text)
    assert script is not None
    assert "ID: (\\\\d+)" in script
