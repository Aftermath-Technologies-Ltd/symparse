import json
import logging
import ast
import re2
from typing import Any
from symparse.ai_client import AIClient

logger = logging.getLogger(__name__)

class CompilationFailedError(Exception):
    """Raised when the LLM cannot write a valid re2 extraction script."""
    pass

def generate_script(text: str, schema: dict, successful_json: dict) -> str:
    """
    Prompts the LLM to write a standalone Python script redefining extraction.
    Strictly sandboxed execution mathematically prevents ReDoS via re2 backend.
    """
    ai_client = AIClient()
    
    prompt = f"""You are a strict code compiler.
We successfully extracted the following data from the input text using a cold start model:
INPUT TEXT:
{text}

SUCCESSFUL EXTRACTED JSON:
{json.dumps(successful_json, indent=2)}

SCHEMA REQUIRED:
{json.dumps(schema, indent=2)}

Write a standalone python script that defines a single function `def extract(text):` which uses ONLY the `re2` library to extract exactly these fields from similar texts next time.
The function must return a completely populated dictionary structured identically to the SCHEMA REQUIRED, carefully building any nested objects and arrays. It must not return a flat map unless the schema is flat.
Use `re2.search()` or `re2.finditer()` with capture groups to pull the exact values. Do not use lookaheads/lookbehinds as re2 does not support them.
Automatically cast the types to match the schema (e.g., int, float, bool). Return None or omit keys if optional and not found.
Do not import any libraries other than `re2`. Return ONLY the python code.
"""
    compiler_schema = {
        "type": "object",
        "properties": {
            "script_code": {
                "type": "string",
                "description": "The full python code block containing `import re2` and the `def extract(text):` function."
            }
        },
        "required": ["script_code"]
    }
    
    try:
        response = ai_client.extract(prompt, compiler_schema)
        script_code = response.get("script_code", "")
        
        if script_code.startswith("```python"):
            script_code = script_code[9:]
        if script_code.startswith("```"):
            script_code = script_code[3:]
        if script_code.endswith("```"):
            script_code = script_code[:-3]
        script_code = script_code.strip()
            
        try:
            ast.parse(script_code)
        except SyntaxError as e:
            raise CompilationFailedError(f"Generated script is not valid Python: {e}")
            
        if "def extract" not in script_code:
            raise CompilationFailedError("Generated script missing 'def extract' function.")
            
        return script_code
        
    except Exception as e:
        logger.error(f"Failed to generate auto-compiled script: {e}")
        raise CompilationFailedError(str(e))
        
def execute_script(script_content: str, text: str, schema: dict) -> dict:
    """
    Executes the sandboxed python extraction script to build the extracted dictionary.
    """
    safe_globals = {
        "__builtins__": {
            "int": int, "float": float, "bool": bool, "list": list, "dict": dict, 
            "set": set, "tuple": tuple, "len": len, "enumerate": enumerate,
            "__import__": __import__
        },
        "re2": re2
    }
    local_env = {}
    
    try:
        exec(script_content, safe_globals, local_env)
        
        extract_func = local_env.get("extract")
        if not extract_func or not callable(extract_func):
            raise ValueError("Script did not define a callable 'extract' function.")
            
        result = extract_func(text)
        if not isinstance(result, dict):
            raise ValueError("Script returned a non-dictionary result.")
            
        return result
    except Exception as e:
        logger.error(f"Failed to execute compiled script: {e}")
        raise ValueError(f"Script execution failed: {e}")
