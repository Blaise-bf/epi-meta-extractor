import json
from pathlib import Path

def load_schema() -> dict:
    """Load the extraction schema from JSON file"""
    schema_path = Path(__file__).parent / "core_schema.json"
    
    with open(schema_path, "r") as f:
        schema = json.load(f)
    
    return schema
