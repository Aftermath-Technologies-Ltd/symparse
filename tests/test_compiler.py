import pytest
from unittest.mock import MagicMock
from symparse.compiler import generate_script, execute_script, CompilationFailedError

def _mock_completion_response(content):
    """Create a mock litellm completion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response

def test_generate_script_success(monkeypatch):
    class MockAIClient:
        def __init__(self, *args, **kwargs):
            self.model = "test-model"
            self.base_url = None
            self.api_key = None
            self.max_tokens = 4000
            
    monkeypatch.setattr('symparse.compiler.AIClient', MockAIClient)
    monkeypatch.setattr('symparse.compiler.completion', lambda **kwargs: _mock_completion_response(
        "import re2\ndef extract(text):\n    return {'name': 'Alice', 'age': 30}"
    ))
    
    schema = {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}}
    text = "My name is Alice and I am 30 years old."
    successful_json = {"name": "Alice", "age": 30}
    
    script = generate_script(text, schema, successful_json)
    
    assert "def extract" in script
    assert "'name': 'Alice'" in script

def test_generate_script_invalid_python(monkeypatch):
    class MockAIClient:
        def __init__(self, *args, **kwargs):
            self.model = "test-model"
            self.base_url = None
            self.api_key = None
            self.max_tokens = 4000
            
    monkeypatch.setattr('symparse.compiler.AIClient', MockAIClient)
    monkeypatch.setattr('symparse.compiler.completion', lambda **kwargs: _mock_completion_response(
        "def extract(text) return {"  # SyntaxError
    ))
    
    schema = {"type": "object"}
    
    with pytest.raises(CompilationFailedError) as exc:
        generate_script("text", schema, {})
    # LLM returns invalid Python → falls through to deterministic compiler → also fails
    assert "failed" in str(exc.value).lower() or "no extractable" in str(exc.value).lower()

def test_execute_script():
    script = """
import re2
def extract(text):
    match1 = re2.search(r'name is (.*?) and', text)
    match2 = re2.search(r'am (\\d+) years', text)
    return {
        "name": match1.group(1) if match1 else None,
        "age": int(match2.group(1)) if match2 else None
    }
"""
    
    text = "My name is Alice and I am 30 years old."
    schema = {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}}
    
    result = execute_script(script, text, schema)
    assert result["name"] == "Alice"
    assert result["age"] == 30
    
def test_execute_script_no_match():
    script = """
import re2
def extract(text):
    match = re2.search(r'name is (.*?) and', text)
    return {"name": match.group(1) if match else None}
"""
    text = "Someone else"
    schema = {"type": "object"}
    result = execute_script(script, text, schema)
    assert result["name"] is None
