"""Tests for schema loader."""

import pytest
from backend.schemas.loader import load_schema, load_effect_schema, list_effect_schemas


class TestLoadSchema:
    """Test generic schema loading."""

    def test_loads_successfully(self):
        schema = load_schema()
        assert isinstance(schema, dict)
        assert "metadata" in schema
        assert "methods" in schema
        assert "analysis" in schema

    def test_has_required_fields(self):
        schema = load_schema()
        assert "title" in schema["metadata"]
        assert "sample_size" in schema["methods"]
        assert "effect_measure" in schema["analysis"]


class TestLoadEffectSchema:
    """Test effect-size-specific schema loading."""

    def test_load_proportion_schema(self):
        schema = load_effect_schema("PROPORTION")
        assert schema is not None
        assert schema["title"] == "Proportion Extraction Schema"
        assert "proportion_data" in schema["properties"]["analysis"]["properties"]

    def test_load_or_schema(self):
        schema = load_effect_schema("OR")
        assert schema is not None
        assert "two_by_two_table" in schema["properties"]["analysis"]["properties"]

    def test_load_md_schema(self):
        schema = load_effect_schema("MD")
        assert schema is not None
        assert "continuous_data" in schema["properties"]["analysis"]["properties"]

    def test_load_hr_schema(self):
        schema = load_effect_schema("HR")
        assert schema is not None
        assert "survival_data" in schema["properties"]["analysis"]["properties"]

    def test_case_insensitive(self):
        schema = load_effect_schema("proportion")
        assert schema is not None
        assert schema["title"] == "Proportion Extraction Schema"

    def test_invalid_effect_type(self):
        assert load_effect_schema("INVALID") is None

    def test_all_schemas_loadable(self):
        for effect_type in list_effect_schemas():
            schema = load_effect_schema(effect_type)
            assert schema is not None, f"Failed to load schema for {effect_type}"
            assert "properties" in schema
            props = schema["properties"]
            assert "metadata" in props
            assert "methods" in props
            assert "analysis" in props


class TestListEffectSchemas:
    """Test listing supported effect schemas."""

    def test_returns_all_measures(self):
        measures = list_effect_schemas()
        assert sorted(measures) == sorted(["PROPORTION", "OR", "RR", "MD", "SMD", "HR"])
