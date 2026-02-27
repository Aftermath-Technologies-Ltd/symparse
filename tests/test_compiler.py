import pytest
import os
import json
import re2
from symparse.compiler import generate_script, execute_script, CompilationFailedError

def test_generate_script_success(monkeypatch):
    class MockAIClient:
        def __init__(self, *args, **kwargs):
            pass
        def extract(self, prompt, schema):
            return {
                "name": "name is (.*?) and",
                "age": "am (\\d+) years"
            }
            
    monkeypatch.setattr('symparse.compiler.AIClient', MockAIClient)
    
    schema = {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}}
    text = "My name is Alice and I am 30 years old."
    successful_json = {"name": "Alice", "age": 30}
    
    script = generate_script(text, schema, successful_json)
    
    data = json.loads(script)
    assert "name" in data
    assert "name is (.*?) and" in data["name"]

def test_generate_script_invalid_re2(monkeypatch):
    class MockAIClient:
        def __init__(self, *args, **kwargs):
            pass
        def extract(self, prompt, schema):
            # Pass a lookbehind which is invalid in re2
            return {
                "name": "(?<=name is ).*?"
            }
            
    monkeypatch.setattr('symparse.compiler.AIClient', MockAIClient)
    
    schema = {"type": "object"}
    
    with pytest.raises(CompilationFailedError) as exc:
        generate_script("text", schema, {})
    assert "invalid RE2" in str(exc.value)

def test_execute_script():
    script_data = {
        "name": "name is (.*?) and",
        "age": "am (\\d+) years"
    }
    script = json.dumps(script_data)
    
    text = "My name is Alice and I am 30 years old."
    
    result = execute_script(script, text)
    assert result["name"] == "Alice"
    assert result["age"] == "30"
    
def test_execute_script_no_match():
    script = json.dumps({"name": "name is (.*?) and"})
    text = "Someone else"
    result = execute_script(script, text)
    assert result["name"] is None
