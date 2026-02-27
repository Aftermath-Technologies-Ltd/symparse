import json
import logging
from enum import Enum
from typing import Any, Dict

from symparse.ai_client import AIClient, ConfidenceDegradationError
from symparse.validator import enforce_schema, SchemaViolationError
from symparse.cache_manager import CacheManager
from symparse.compiler import generate_script, execute_script

logger = logging.getLogger(__name__)

class GracefulDegradationMode(Enum):
    HALT = "halt"
    PASSTHROUGH = "passthrough"

class EngineFailure(Exception):
    """Raised when engine fails and degradation mode is HALT."""
    pass

def process_stream(
    input_text: str, 
    schema_dict: dict, 
    compile: bool = False,
    force_ai: bool = False,
    max_retries: int = 3,
    degradation_mode: GracefulDegradationMode = GracefulDegradationMode.HALT
) -> Dict[str, Any]:
    """
    Entry point handling routing logic. 
    Routes Fast Paths vs AI Paths. ReDoS-proof regex zero copies strings in C++.
    """
    ai_client = AIClient()
    cache_manager = CacheManager()
    
    # Fast path logic
    if not force_ai:
        cached_script = cache_manager.fetch_script(schema_dict, input_text)
        if cached_script:
            logger.info("Executing Fast Path via cached script")
            try:
                fast_json = execute_script(cached_script, input_text)
                enforce_schema(fast_json, schema_dict)
                return fast_json
            except SchemaViolationError as e:
                logger.warning(f"Fast path failed validation ({e}). Falling back to AI Path and purging cache.")
                cache_manager.delete_script(schema_dict)
            except Exception as e:
                logger.warning(f"Fast path failed execution ({e}). Falling back to AI Path and purging cache.")
                cache_manager.delete_script(schema_dict)

    # AI Path (Cold Start)
    logger.info("Routing through AI Path (Cold Start)")
    last_error_message = ""
    prompt_text = input_text
    
    for attempt in range(max_retries):
        try:
            current_prompt = prompt_text
            if last_error_message:
                current_prompt += f"\n\nERROR FROM PREVIOUS ATTEMPT:\n{last_error_message}\nPlease fix your output to strictly adhere to the schema."
            
            extracted_json = ai_client.extract(current_prompt, schema_dict)
            
            # Pass to validator
            enforce_schema(extracted_json, schema_dict)
            
            # Auto-compiler logic
            if compile:
                logger.info("Compiling extraction to local RE2 script cache")
                generated_script = generate_script(input_text, schema_dict, extracted_json)
                cache_manager.save_script(schema_dict, input_text, generated_script)
                
            return extracted_json
            
        except (SchemaViolationError, ConfidenceDegradationError) as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            last_error_message = str(e)
            
        except Exception as e:
            logger.error(f"Unexpected error during extraction: {e}")
            break

    # If we get here, validation utterly failed after retries
    if degradation_mode == GracefulDegradationMode.HALT:
        raise EngineFailure(f"Failed to extract matching schema after {max_retries} attempts. Last error: {last_error_message}")
    elif degradation_mode == GracefulDegradationMode.PASSTHROUGH:
        return {
            "error": "Validation failed",
            "last_error": last_error_message,
            "raw_text": input_text
        }

