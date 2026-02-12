import pytest
from backend.schemas.loader import load_schema

def test_schema_loads_successfully():
    schema = load_schema()
    assert isinstance(schema, dict)
    assert "metadata" in schema
    assert "methods" in schema
    assert "analysis" in schema

def test_schema_contains_required_fields():
    schema = load_schema()
    assert "study_id" in schema["metadata"]
    assert "sample_size" in schema["methods"]
    assert "effect_measure" in schema["analysis"]
