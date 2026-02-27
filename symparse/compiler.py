import json
import logging
import re2
from symparse.ai_client import AIClient

logger = logging.getLogger(__name__)

class CompilationFailedError(Exception):
    """Raised when the LLM cannot write a valid re2 extraction script."""
    pass

def generate_script(text: str, schema: dict, successful_json: dict) -> str:
    """
    Prompts the LLM to write a linearly bound re2 regex script.
    Strictly sandboxed execution mathematically prevents ReDoS via re2 backend.
    """
    ai_client = AIClient()
    
    # We ask the LLM to generate a dictionary of key -> regex pattern
    # It must map the schema properties to valid re2 capture expressions.
    prompt = f"""You are a strict code compiler.
We successfully extracted the following data from the input text using a cold start model:
INPUT TEXT:
{text}

SUCCESSFUL EXTRACTED JSON:
{json.dumps(successful_json, indent=2)}

SCHEMA REQUIRED:
{json.dumps(schema, indent=2)}

Write linearly bound re2 regular expressions to extract exactly these fields next time.
Return a JSON object where keys are the schema property names and values are the re2 regex strings containing exactly one capture group '()' each. Do not use lookaheads/lookbehinds as re2 does not support them.
"""
    compiler_schema = {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "description": "Mapping of field name to a single re2 regex pattern containing one capture group."
    }
    
    try:
        # We reuse the robust structured parsing from ai_client
        compiled_regexes = ai_client.extract(prompt, compiler_schema)
        
        # Verify all regexes compile in re2 to mathematically prevent ReDoS
        for key, pattern in compiled_regexes.items():
            try:
                # `re2.compile` throws if invalid or if using unsupported features
                re2.compile(pattern)
            except Exception as e:
                raise CompilationFailedError(f"Generated regex for {key} is invalid RE2: {e}")
                
        # Return serialized regex dictionary representing the "script"
        return json.dumps(compiled_regexes)
        
    except Exception as e:
        logger.error(f"Failed to generate auto-compiled script: {e}")
        raise CompilationFailedError(str(e))
        
def execute_script(script_content: str, text: str) -> dict:
    """
    Executes the sandboxed re2 extraction script.
    """
    compiled_regexes = json.loads(script_content)
    result = {}
    for key, pattern in compiled_regexes.items():
        regex = re2.compile(pattern)
        match = regex.search(text)
        if match and match.groups():
            # For simplicity, just grab the first capture group. 
            # Sub-type parsing (e.g., int conversions) happens later via the validator/engine.
            result[key] = match.group(1)
        else:
            result[key] = None
    return result
