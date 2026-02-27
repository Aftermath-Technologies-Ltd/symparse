import json
import logging
from enum import Enum
from typing import Any, Dict

from symparse.ai_client import AIClient, ConfidenceDegradationError
from symparse.validator import enforce_schema, SchemaViolationError

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
    Passes data to AI Client, validates, and retries on failure.
    """
    ai_client = AIClient()
    
    # Fast path logic placeholder
    if not force_ai:
        # TODO: Implement Tier 1/2 semantic caching and execution here
        pass

    # AI Path (Cold Start)
    last_error_message = ""
    prompt_text = input_text
    
    for attempt in range(max_retries):
        try:
            # Reflexion loop: attach the last error if any
            current_prompt = prompt_text
            if last_error_message:
                current_prompt += f"\n\nERROR FROM PREVIOUS ATTEMPT:\n{last_error_message}\nPlease fix your output to strictly adhere to the schema."
            
            extracted_json = ai_client.extract(current_prompt, schema_dict)
            
            # Pass to validator
            enforce_schema(extracted_json, schema_dict)
            
            # Auto-compiler logic placeholder
            if compile:
                # TODO: compiler.generate_script(...)
                pass
                
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
