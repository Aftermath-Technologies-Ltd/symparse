import json
import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

class ConfidenceDegradationError(Exception):
    """Raised when structured generation passes schema but fails the logprob Confidence Egress Gate."""
    pass

class AIClient:
    def __init__(self, base_url: str = None, api_key: str = None, model: str = None, logprob_threshold: float = -0.5):
        # Default to local containerized endpoints if not provided
        self.base_url = base_url or os.getenv("SYMPARSE_AI_BASE_URL", "http://localhost:11434/v1")
        self.api_key = api_key or os.getenv("SYMPARSE_AI_API_KEY", "ollama")
        self.model = model or os.getenv("SYMPARSE_AI_MODEL", "llama3")
        self.logprob_threshold = logprob_threshold
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def extract(self, text: str, schema: dict) -> dict:
        """
        Handles LLM extraction enforcing structured generation.
        Implements a Confidence Egress Gate using token logprobs.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a perfectly rigid data extraction tool. Extract ONLY matching data into the required JSON schema structure."},
                {"role": "user", "content": f"Extract structured data from the following text:\n\n{text}"}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "extraction_schema",
                    "schema": schema,
                    "strict": True
                }
            },
            temperature=0.0,
            logprobs=True,
            top_logprobs=1
        )
        
        choice = response.choices[0]
        raw_json = choice.message.content
        
        # Confidence Egress Gate
        if choice.logprobs and choice.logprobs.content:
            for token_logprob in choice.logprobs.content:
                # Egress Gate check against threshold
                if token_logprob.logprob < self.logprob_threshold:
                    raise ConfidenceDegradationError(
                        f"Semantic degradation detected. Token '{token_logprob.token}' logprob ({token_logprob.logprob:.2f}) is below threshold ({self.logprob_threshold:.2f})."
                    )

        return json.loads(raw_json)
