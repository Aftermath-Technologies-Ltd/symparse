# symparse

Symparse is a self-optimizing Unix pipeline tool that routes between an AI Path and a Fast Path using a neurosymbolic gate for validation.

## Overivew
The tool receives unstructured text from `stdin`, enforces it into a strictly typed JSON structure defined by a user-provided schema, and outputs to `stdout`. 

## Features
- Validates text data against user-provided JSON schemas
- CLI natively supports Unix pipelines
- Subcommands for cache management

## Installation
```bash
pip install -e .
```

## Usage
`symparse` accepts data directly via `stdin`. The only required argument is `--schema` pointing to your target structure.

```bash
cat unstructured_log.txt | symparse run --schema log_schema.json
```

### Options
* `--schema <path>`: Required. Path to the local JSON schema file.
* `--compile`: Compiles a fast-path script on successful extraction.
* `--force-ai`: Bypasses the local fast-path cache and forces AI execution.

### Cache Management
You can list compiled extraction scripts or clear the compilation cache.
```bash
symparse cache list
symparse cache clear
```

## Python API
Symparse provides a core Internal Python API which you can use directly.

### Validator
```python
from symparse.validator import enforce_schema, SchemaViolationError

schema = {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]}
data = {"status": "success"}

# Returns True or raises SchemaViolationError
enforce_schema(data, schema)
```

### AI Client
```python
from symparse.ai_client import AIClient, ConfidenceDegradationError

client = AIClient(base_url="http://localhost:11434/v1", model="llama3")

try:
    data = client.extract("raw text", schema)
except ConfidenceDegradationError as e:
    print("AI output passed strict schema but semantically degraded.")
```
