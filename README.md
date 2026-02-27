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
from symparse.engine import process_stream, GracefulDegradationMode

# Returns dict or raises EngineFailure based on degradation mode
result = process_stream(
    "unstructured data",
    schema,
    max_retries=3,
    degradation_mode=GracefulDegradationMode.PASSTHROUGH
)
```

### Cache Management
Symparse natively implements a two-tier cache with explicit UNIX process locking to handle pipeline streaming.
```python
from symparse.cache_manager import CacheManager

manager = CacheManager()
manager.save_script(schema, "example text", "def extract(txt): ...") # Lock serialization
manager.fetch_script(schema, "example text") # Uses Two-Tier Collision Detection
manager.clear_cache()
```

### Auto-Compiler
The Auto-Compiler generates deterministic, mathematically ReDoS-proof extraction scripts without needing `eval()`.
```python
from symparse.compiler import generate_script, execute_script

script = generate_script(text="...", schema={...}, successful_json={...})
fast_result = execute_script(script, text="...")
```
