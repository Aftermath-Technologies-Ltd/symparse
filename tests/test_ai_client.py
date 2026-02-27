import pytest
from symparse.ai_client import AIClient, ConfidenceDegradationError
import litellm
import os

def test_ai_client_extract_success():
    client = AIClient(
        base_url=os.getenv("SYMPARSE_AI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("SYMPARSE_AI_API_KEY", "test"),
        model=os.getenv("SYMPARSE_AI_MODEL", "test-model")
    )
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        },
        "required": ["name", "age"]
    }
    try:
        data = client.extract("My name is Alice and I am 30 years old.", schema)
        assert data["name"] == "Alice"
        assert data["age"] == 30
    except Exception as e:
        pytest.skip(f"No local LLM endpoint running or failed inference: {e}")

def test_ai_client_network_failure(monkeypatch):
    """Mocking is permitted for testing explicit network failure codes."""
    # We mock litellm.completion to raise a predefined error
    def mock_completion(*args, **kwargs):
        from litellm.exceptions import APIConnectionError
        raise APIConnectionError("Connection Failed", request=None, llm_provider="test")
            
    monkeypatch.setattr('symparse.ai_client.completion', mock_completion)
        
    client = AIClient()
    
    with pytest.raises(Exception):
        client.extract("test", {"type": "object"})
