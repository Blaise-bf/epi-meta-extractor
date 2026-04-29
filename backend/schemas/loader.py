import json
from pathlib import Path
from typing import Optional

# Mapping of effect measures to their schema files
EFFECT_SCHEMA_MAP = {
    "PROPORTION": "proportion_schema.json",
    "OR": "or_rr_schema.json",
    "RR": "or_rr_schema.json",
    "MD": "md_smd_schema.json",
    "SMD": "md_smd_schema.json",
    "HR": "hr_schema.json",
}


def load_schema() -> dict:
    """Load the generic extraction schema from JSON file"""
    schema_path = Path(__file__).parent / "core_schema.json"

    with open(schema_path, "r") as f:
        schema = json.load(f)

    return schema


def load_effect_schema(effect_type: str) -> Optional[dict]:
    """Load the effect-size-specific extraction schema.

    Args:
        effect_type: One of PROPORTION, OR, RR, MD, SMD, HR

    Returns:
        The JSON schema dict, or None if effect_type is not recognized.
    """
    effect_type_upper = effect_type.upper()
    schema_filename = EFFECT_SCHEMA_MAP.get(effect_type_upper)

    if not schema_filename:
        return None

    schema_path = Path(__file__).parent / schema_filename

    if not schema_path.exists():
        return None

    with open(schema_path, "r") as f:
        schema = json.load(f)

    return schema


def list_effect_schemas() -> list[str]:
    """Return a list of all supported effect measure types."""
    return list(EFFECT_SCHEMA_MAP.keys())
