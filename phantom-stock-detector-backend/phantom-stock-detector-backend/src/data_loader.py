"""Small wrapper around the schema adapter for pipeline callers."""
from .schema_adapter import load_standardized_data

def load_data(schema_path):
    """Load all required and optional standardized input tables."""
    return load_standardized_data(schema_path)
