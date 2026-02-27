import pytest
from symparse.engine import process_stream, EngineFailure, GracefulDegradationMode

def test_process_stream_success(monkeypatch):
    class MockAIClient:
        def __init__(self, *args, **kwargs):
            pass
        def extract(self, text, schema):
            return {"name": "Bob", "age": 40}
    
    monkeypatch.setattr('symparse.engine.AIClient', MockAIClient)
    
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"]
    }
    
    result = process_stream("test input", schema)
    assert result == {"name": "Bob", "age": 40}

def test_process_stream_degradation_halt(monkeypatch):
    class MockAIClient:
        def __init__(self, *args, **kwargs):
            pass
        def extract(self, text, schema):
            # Return invalid data to trigger validation failure
            return {"name": "Bob"}
    
    monkeypatch.setattr('symparse.engine.AIClient', MockAIClient)
    
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"]
    }
    
    with pytest.raises(EngineFailure) as exc:
        process_stream("test input", schema, max_retries=1, degradation_mode=GracefulDegradationMode.HALT)
    assert "Failed to extract matching schema after 1 attempts" in str(exc.value)
    
def test_process_stream_degradation_passthrough(monkeypatch):
    class MockAIClient:
        def __init__(self, *args, **kwargs):
            pass
        def extract(self, text, schema):
            # Return invalid data
            return {"name": "Bob"}
            
    monkeypatch.setattr('symparse.engine.AIClient', MockAIClient)
    
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"]
    }
    
    result = process_stream("test input", schema, max_retries=1, degradation_mode=GracefulDegradationMode.PASSTHROUGH)
    assert "error" in result
    assert result["error"] == "Validation failed"
    assert result["raw_text"] == "test input"
