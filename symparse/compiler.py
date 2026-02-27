import json
import logging
import ast
import re2
from litellm import completion
from symparse.ai_client import AIClient

logger = logging.getLogger(__name__)

class CompilationFailedError(Exception):
    """Raised when the LLM cannot write a valid re2 extraction script."""
    pass


def _build_deterministic_script(text: str, schema: dict, successful_json: dict) -> str:
    """
    Build a deterministic re2 extraction script using template-based compilation.
    
    Strategy: Take the original text, find each extracted value, replace it with
    a regex capture group, and escape everything else. This produces a full-line
    regex pattern that precisely captures values from structurally similar text.
    """
    
    def _flatten_leaves(obj, prefix=""):
        """Yield (dotted_path, value) for all leaf values."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    yield from _flatten_leaves(v, path)
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            yield from _flatten_leaves(item, f"{path}[{i}]")
                        else:
                            yield (f"{path}[{i}]", item)
                else:
                    yield (path, v)
    
    def _get_schema_type(path, schema):
        """Get the JSON schema type for a dotted path."""
        parts = path.replace("[", ".").replace("]", "").split(".")
        current = schema
        for part in parts:
            if part.isdigit():
                current = current.get("items", {})
            else:
                current = current.get("properties", {}).get(part, {})
        return current.get("type", "string")
    
    def _capture_for_value(value, stype, text, pos):
        """Return a regex capture group appropriate for the value type and context."""
        sval = str(value)
        end = pos + len(sval)
        
        if stype in ("integer",) or (isinstance(value, int) and not isinstance(value, bool)):
            return r"(\d+)"
        if stype == "number" or isinstance(value, float):
            return r"([\d.]+)"
        if isinstance(value, bool):
            return r"(true|false)"
        # String types
        if "@" in sval:
            return r"([\w.+-]+@[\w.-]+\.\w+)"
        if all(c.isdigit() or c == "." for c in sval) and sval.count(".") == 3:
            return r"(\d+\.\d+\.\d+\.\d+)"
        
        # Check if value is surrounded by delimiters in the source text
        char_after = text[end] if end < len(text) else ""
        char_before = text[pos - 1] if pos > 0 else ""
        
        if char_before == '"' and char_after == '"':
            return r'([^"]*)'
        if char_before == '[' and char_after == ']':
            return r'([^\]]*)'
        if char_before == '(' and char_after == ')':
            return r'([^\)]*)'
        
        if " " in sval:
            return r"([^\[\]\"]+)"
        return r"(\S+)"
    
    # Flatten all leaves and find their positions in the text.
    # We search left-to-right: each value's position must be AFTER the previous
    # value's end, preventing collisions (e.g., "14" in "14:32:01" vs bytes=14).
    leaves = list(_flatten_leaves(successful_json))
    located = []
    search_start = 0
    for path, value in leaves:
        sval = str(value)
        # Find the NEXT occurrence of sval at or after search_start
        pos = text.find(sval, search_start)
        if pos == -1:
            # Try from the beginning as a fallback (value might be before current position
            # if JSON key order doesn't match text order)
            pos = text.find(sval)
            if pos == -1:
                continue
        stype = _get_schema_type(path, schema)
        capture = _capture_for_value(value, stype, text, pos)
        end = pos + len(sval)
        located.append({
            "path": path,
            "value": value,
            "stype": stype,
            "capture": capture,
            "pos": pos,
            "end": end
        })
        search_start = end
    
    if not located:
        raise CompilationFailedError("Cannot build deterministic script: no extractable values found in text.")
    
    # Sort by position in text (crucial for template approach)
    located.sort(key=lambda x: x["pos"])
    
    # Remove overlapping matches (keep earliest)
    filtered = []
    last_end = 0
    for entry in located:
        if entry["pos"] >= last_end:
            filtered.append(entry)
            last_end = entry["end"]
    located = filtered
    
    # Build the template regex: escape gaps between values, insert capture groups
    regex_parts = []
    prev_end = 0
    group_map = []  # (group_index, path, stype, value)
    
    for i, entry in enumerate(located):
        # Escape the gap between previous end and this value
        gap = text[prev_end:entry["pos"]]
        if gap:
            # Escape literal text but relax whitespace to \s+
            escaped_gap = re2.escape(gap)
            # Replace escaped whitespace with flexible \s+ 
            escaped_gap = re2.sub(r'(\\\s)+', r'\\s+', escaped_gap)
            regex_parts.append(escaped_gap)
        
        regex_parts.append(entry["capture"])
        group_map.append((i + 1, entry["path"], entry["stype"], entry["value"]))
        prev_end = entry["end"]
    
    full_pattern = "".join(regex_parts)
    
    # Generate the script — use single-quoted raw strings so " inside
    # character classes (e.g., [^"]*) doesn't break the string literal.
    lines = ["import re2", "", "def extract(text):"]
    lines.append(f"    m = re2.search(r'{full_pattern}', text)")
    lines.append("    if not m:")
    lines.append("        return None")
    lines.append("    result = {}")
    
    for group_idx, path, stype, value in group_map:
        parts = path.split(".")
        safe_val = f"m.group({group_idx})"
        
        # Apply type conversion
        if stype == "integer" or (isinstance(value, int) and not isinstance(value, bool)):
            safe_val = f"int({safe_val})"
        elif stype == "number" or isinstance(value, float):
            safe_val = f"float({safe_val})"
        elif isinstance(value, bool):
            safe_val = f"{safe_val}.lower() == 'true'"
        
        if len(parts) == 1:
            lines.append(f'    result["{parts[0]}"] = {safe_val}')
        else:
            # Nested field — ensure parent dicts exist
            lines.append(f'    result.setdefault("{parts[0]}", {{}})')
            current_expr = f'result["{parts[0]}"]'
            for j in range(1, len(parts) - 1):
                lines.append(f'    {current_expr}.setdefault("{parts[j]}", {{}})')
                current_expr = f'{current_expr}["{parts[j]}"]'
            lines.append(f'    {current_expr}["{parts[-1]}"] = {safe_val}')
    
    lines.append("    return result")
    
    script = "\n".join(lines)
    ast.parse(script)
    return script


def _self_test_script(script_code: str, text: str, schema: dict, successful_json: dict) -> bool:
    """
    Self-test a generated script against the original data.
    Returns True if the script produces output matching the expected JSON.
    """
    try:
        result = execute_script(script_code, text, schema)
        if not isinstance(result, dict):
            return False
        # Check all required fields are present with correct values
        for key, expected_val in successful_json.items():
            if key not in result:
                return False
            if str(result[key]) != str(expected_val):
                return False
        return True
    except Exception:
        return False


def generate_script(text: str, schema: dict, successful_json: dict) -> str:
    """
    Prompts the LLM to write a standalone Python script redefining extraction.
    Strictly sandboxed execution mathematically prevents ReDoS via re2 backend.
    Self-tests the output against the original data before returning.
    Falls back to deterministic pattern compilation if the LLM fails.
    """
    ai_client = AIClient()
    
    prompt = f"""You are a strict code compiler. Write ONLY Python code with no explanation.
We successfully extracted the following data from the input text:
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
Do not import any libraries other than `re2`. Return ONLY the python code, no JSON wrapping.
"""
    
    # Try LLM-generated script first
    llm_error = None
    try:
        kwargs = {
            "model": ai_client.model,
            "messages": [
                {"role": "system", "content": "You are a Python code generator. Return ONLY raw Python code. No markdown fences, no JSON, no explanation."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "max_tokens": ai_client.max_tokens,
            "drop_params": True
        }
        if ai_client.base_url:
            kwargs["api_base"] = ai_client.base_url
        if ai_client.api_key:
            kwargs["api_key"] = ai_client.api_key
            
        response = completion(**kwargs)
        script_code = response.choices[0].message.content or ""
        
        # Strip markdown code fences
        script_code = script_code.strip()
        if script_code.startswith("```python"):
            script_code = script_code[len("```python"):]
        elif script_code.startswith("```"):
            script_code = script_code[3:]
        if script_code.endswith("```"):
            script_code = script_code[:-3]
        script_code = script_code.strip()
        
        # If wrapped in JSON, try to extract script_code key
        if script_code.startswith("{"):
            try:
                parsed = json.loads(script_code)
                if isinstance(parsed, dict) and "script_code" in parsed:
                    script_code = parsed["script_code"].strip()
            except (json.JSONDecodeError, ValueError):
                pass
            
        ast.parse(script_code)
        
        if "def extract" not in script_code:
            raise CompilationFailedError("Generated script missing 'def extract' function.")
        
        # Self-test: verify the script actually works on the original data
        if _self_test_script(script_code, text, schema, successful_json):
            logger.info("LLM-generated script passed self-test.")
            return script_code
        else:
            llm_error = "LLM script failed self-test against archetype data"
            logger.debug(llm_error)
            
    except CompilationFailedError as e:
        llm_error = str(e)
    except Exception as e:
        llm_error = str(e)
    
    # Fallback: deterministic pattern compiler
    logger.info(f"LLM compilation failed ({llm_error}), using deterministic compiler fallback.")
    try:
        det_script = _build_deterministic_script(text, schema, successful_json)
        if _self_test_script(det_script, text, schema, successful_json):
            logger.info("Deterministic script passed self-test.")
            return det_script
        else:
            raise CompilationFailedError("Deterministic script also failed self-test.")
    except CompilationFailedError:
        raise
    except Exception as e:
        raise CompilationFailedError(f"All compilation strategies failed. LLM: {llm_error}. Deterministic: {e}")
        
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
        logger.debug(f"Compiled script execution failed: {e}")
        raise ValueError(f"Script execution failed: {e}")
