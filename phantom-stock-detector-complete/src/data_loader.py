"""Small wrapper around the schema adapter."""
from .schema_adapter import load_all_tables

def load_data(schema_path, project_root=None):
    """Load all configured CSV tables into standardized DataFrames."""
    return load_all_tables(schema_path, project_root=project_root)
