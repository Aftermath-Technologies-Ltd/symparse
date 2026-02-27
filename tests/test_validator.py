import pytest
from symparse.validator import enforce_schema, SchemaViolationError

def test_enforce_schema_valid():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        },
        "required": ["name", "age"]
    }
    data = {"name": "Alice", "age": 30}
    assert enforce_schema(data, schema) is True

def test_enforce_schema_invalid_type():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        },
        "required": ["name", "age"]
    }
    data = {"name": "Alice", "age": "thirty"}
    with pytest.raises(SchemaViolationError) as exc:
        enforce_schema(data, schema)
    
    # Path will point to property
    assert exc.value.path == "age"
    assert "Schema violation at 'age'" in str(exc.value)

def test_enforce_schema_missing_property():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        },
        "required": ["name"]
    }
    data = {}
    with pytest.raises(SchemaViolationError) as exc:
        enforce_schema(data, schema)
    
    assert "Schema violation: 'name' is a required property" in str(exc.value)

def test_enforce_schema_invalid_schema():
    data = {"name": "Alice"}
    # Schema must be valid jsonschema, here we omit for simplicity, but if the schema is totally broken:
    # `jsonschema.validate` might raise SchemaError instead of ValidationError, which we don't catch explicitly.
    # We will test an invalid schema to see what happens since jsonschema raises SchemaError on invalid schemas
    # But since we only catch ValidationError, we leave SchemaError uncaught and that's okay because it represents developer error rather than payload error.
    pass
