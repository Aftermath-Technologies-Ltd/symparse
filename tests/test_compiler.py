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
                "script_code": "import re2\ndef extract(text):\n    return {'name': 'Alice', 'age': 30}"
            }
            
    monkeypatch.setattr('symparse.compiler.AIClient', MockAIClient)
    
    schema = {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}}
    text = "My name is Alice and I am 30 years old."
    successful_json = {"name": "Alice", "age": 30}
    
    script = generate_script(text, schema, successful_json)
    
    assert "def extract" in script
    assert "'name': 'Alice'" in script

def test_generate_script_invalid_python(monkeypatch):
    class MockAIClient:
        def __init__(self, *args, **kwargs):
            pass
        def extract(self, prompt, schema):
            return {
                "script_code": "def extract(text) return {" # SyntaxError
            }
            
    monkeypatch.setattr('symparse.compiler.AIClient', MockAIClient)
    
    schema = {"type": "object"}
    
    with pytest.raises(CompilationFailedError) as exc:
        generate_script("text", schema, {})
    assert "not valid Python" in str(exc.value)

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
