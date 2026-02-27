import json
import logging
import os
import configparser
from pathlib import Path
from litellm import completion
import litellm

# Suppress annoying debug output from litellm if any
litellm.suppress_debug_info = True

logger = logging.getLogger(__name__)

class ConfidenceDegradationError(Exception):
    """Raised when structured generation passes schema but fails the logprob Confidence Egress Gate."""
    pass

class AIClient:
    def __init__(self, base_url: str = None, api_key: str = None, model: str = None, logprob_threshold: float = None, max_tokens: int = 4000):
        config = configparser.ConfigParser()
        config_path = Path.home() / ".symparserc"
        if config_path.exists():
            config.read(config_path)
            
        ai_config = config["AI"] if "AI" in config else {}
            
        # Precedence: Init Args -> Env Vars -> Config File -> Fallback Default
        self.base_url = base_url or os.getenv("SYMPARSE_AI_BASE_URL") or ai_config.get("base_url")
        self.api_key = api_key or os.getenv("SYMPARSE_AI_API_KEY") or ai_config.get("api_key")
        
        # For litellm, we specify providers in the model name (e.g., openai/gpt-4o, ollama/gemma3:1b)
        # We assume if someone was relying on old fallback it meant an openai compatible proxy
        self.model = model or os.getenv("SYMPARSE_AI_MODEL") or ai_config.get("model", "ollama/gemma3:4b")
        
        if logprob_threshold is not None:
            self.logprob_threshold = logprob_threshold
        elif "SYMPARSE_CONFIDENCE_THRESHOLD" in os.environ:
            self.logprob_threshold = float(os.environ["SYMPARSE_CONFIDENCE_THRESHOLD"])
        else:
            self.logprob_threshold = -2.0
        
        self.max_tokens = max_tokens

    def extract(self, text: str, schema: dict) -> dict:
        """
        Handles LLM extraction enforcing structured generation.
        Implements a Confidence Egress Gate using token logprobs.
        """
        # Build a concrete example showing the model what output shape to produce
        def _build_example(props: dict) -> dict:
            """Recursively build example object from schema properties."""
            obj = {}
            for key, prop in props.items():
                ptype = prop.get("type", "string")
                if ptype == "string":
                    obj[key] = f"<extracted {key}>"
                elif ptype == "number":
                    obj[key] = 0
                elif ptype == "integer":
                    obj[key] = 0
                elif ptype == "boolean":
                    obj[key] = False
                elif ptype == "array":
                    items_schema = prop.get("items", {})
                    if items_schema.get("type") == "object" and "properties" in items_schema:
                        obj[key] = [_build_example(items_schema["properties"])]
                    else:
                        obj[key] = [f"<extracted {key} item>"]
                elif ptype == "object" and "properties" in prop:
                    obj[key] = _build_example(prop["properties"])
                elif ptype == "object":
                    obj[key] = {}
                else:
                    obj[key] = f"<extracted {key}>"
            return obj

        properties = schema.get("properties", {})
        example_obj = _build_example(properties)
        
        required_fields = schema.get("required", list(properties.keys()))
        field_list = ", ".join(f'"{f}"' for f in required_fields)
        example_output = json.dumps(example_obj, indent=2)
        
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a data extraction tool. Given raw text, extract values into a JSON object. Respond with ONLY the JSON object. No schema definitions, no markdown, no explanation."},
                {"role": "user", "content": (
                    f"Extract the following fields from the text below: {field_list}\n\n"
                    f"Return a JSON object like this example:\n{example_output}\n\n"
                    f"Text to extract from:\n{text}\n\n"
                    f"Respond with ONLY the JSON object containing the extracted values:"
                )}
            ],
            "temperature": 0.0,
            "max_tokens": self.max_tokens,
            # drop_params silently drops logprobs/top_logprobs for providers that don't support them
            "logprobs": True,
            "top_logprobs": 1,
            "drop_params": True
        }
        
        if self.base_url:
            kwargs["api_base"] = self.base_url
        if self.api_key:
            kwargs["api_key"] = self.api_key
            
        try:
            response = completion(**kwargs)
        except Exception as e:
            logger.error(f"LiteLLM backend failure: {e}")
            raise
        
        choice = response.choices[0]
        # Some litellm providers might return dicts differently, fallback safely
        raw_json = choice.message.content if hasattr(choice.message, 'content') else choice.get("message", {}).get("content", "{}")
        
        # Strip markdown code fences that some models wrap around JSON output
        if raw_json:
            raw_json = raw_json.strip()
            if raw_json.startswith("```"):
                # Remove opening fence (```json or ```)
                first_newline = raw_json.find("\n")
                if first_newline != -1:
                    raw_json = raw_json[first_newline + 1:]
                # Remove closing fence
                if raw_json.endswith("```"):
                    raw_json = raw_json[:-3]
                raw_json = raw_json.strip()
        
        # Confidence Egress Gate
        if hasattr(choice, 'logprobs') and choice.logprobs and hasattr(choice.logprobs, 'content') and choice.logprobs.content:
            logprobs = [token.logprob for token in choice.logprobs.content if hasattr(token, 'logprob')]
            if logprobs:
                avg_logprob = sum(logprobs) / len(logprobs)
                
                # Egress Gate check against threshold
                if avg_logprob < self.logprob_threshold:
                    raise ConfidenceDegradationError(
                        f"Semantic degradation detected. Average logprob ({avg_logprob:.2f}) is below threshold ({self.logprob_threshold:.2f})."
                    )

        return json.loads(raw_json)
