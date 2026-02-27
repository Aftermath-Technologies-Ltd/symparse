import pytest
from symparse.ai_client import AIClient, ConfidenceDegradationError
import openai
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
    except openai.APIConnectionError:
        pytest.skip("No local LLM endpoint running on localhost:11434")
    except openai.NotFoundError:
        pytest.skip("Model not found on local endpoint")

def test_ai_client_network_failure(monkeypatch):
    """Mocking is permitted for testing explicit network failure codes."""
    # We mock the chat.completions.create to raise a ConnectionError
    class MockChatCompletions:
        def create(self, *args, **kwargs):
            raise openai.APIConnectionError(request=None)
            
    class MockChat:
        completions = MockChatCompletions()
        
    class MockClient:
        chat = MockChat()
        
    client = AIClient()
    monkeypatch.setattr(client, 'client', MockClient())
    
    with pytest.raises(openai.APIConnectionError):
        client.extract("test", {"type": "object"})
