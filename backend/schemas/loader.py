import json
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas/core_schema.json"

def load_schema() -> dict:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError("Extraction schema not found.")
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)
