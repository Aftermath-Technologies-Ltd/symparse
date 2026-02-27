import jsonschema

class SchemaViolationError(Exception):
    """Raised when the parsed JSON data does not conform to the schema."""
    
    def __init__(self, message: str, path: str = ""):
        self.message = message
        self.path = path
        super().__init__(f"Schema violation at '{path}': {message}" if path else f"Schema violation: {message}")

def enforce_schema(data: dict, schema: dict) -> bool:
    """
    Validates a dictionary against a JSON schema.
    Returns True if valid. Raises SchemaViolationError on failure.
    """
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True
    except jsonschema.exceptions.ValidationError as e:
        path = ".".join(str(p) for p in e.path) if e.path else ""
        raise SchemaViolationError(e.message, path) from e
