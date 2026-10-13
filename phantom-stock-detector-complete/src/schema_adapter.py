"""Map user-provided CSV column names into the project's standard schema."""
import json
from pathlib import Path
import pandas as pd

REQUIRED_FIELDS = {
    "sales": ["date", "store_id", "sku_id", "units_sold"],
    "inventory": ["date", "store_id", "sku_id", "on_hand"],
}
OPTIONAL_FIELDS = {
    "promotions": ["date", "store_id", "sku_id", "promo_active"],
    "stores": ["store_id", "store_format", "store_size", "city_tier"],
    "products": ["sku_id", "sku_name", "category", "selling_price"],
    "ground_truth": ["date", "store_id", "sku_id", "is_phantom"],
}

def read_schema(schema_path):
    """Load and return a schema JSON file."""
    path = Path(schema_path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Schema file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Schema JSON is invalid: {path}: {exc}") from exc

def load_mapped_table(project_root, table_name, table_config, required_fields):
    """Read one configured CSV and rename mapped source columns to standard names."""
    if not table_config:
        if required_fields:
            raise ValueError(f"Schema is missing required section '{table_name}'.")
        return None
    file_value = table_config.get("file")
    if not file_value:
        if required_fields:
            raise ValueError(f"Schema section '{table_name}' must include a 'file' value.")
        return None
    path = Path(file_value)
    if not path.is_absolute():
        path = Path(project_root) / path
    if not path.exists():
        if required_fields:
            raise ValueError(f"Required {table_name} CSV file not found: {path}")
        return None
    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        raise ValueError(f"Could not read {table_name} CSV '{path}': {exc}") from exc

    rename_map = {}
    missing = []
    for standard_name in required_fields:
        source_name = table_config.get(standard_name)
        if not source_name:
            missing.append(f"mapping for '{standard_name}'")
        elif source_name not in raw.columns:
            missing.append(f"column '{source_name}' (mapped to '{standard_name}')")
        else:
            rename_map[source_name] = standard_name
    if missing:
        raise ValueError(
            f"{table_name} file '{path}' is missing required fields/columns: "
            + ", ".join(missing)
            + f". Available columns: {list(raw.columns)}"
        )
    # Map optional configured columns only when the source column exists.
    for standard_name in OPTIONAL_FIELDS.get(table_name, []):
        source_name = table_config.get(standard_name)
        if source_name and source_name in raw.columns:
            rename_map[source_name] = standard_name
    data = raw.rename(columns=rename_map).copy()
    keep = list(dict.fromkeys(field for field in required_fields + OPTIONAL_FIELDS.get(table_name, []) if field in data.columns))
    data = data[keep]
    for field in ("date",):
        if field in data.columns:
            data[field] = pd.to_datetime(data[field], errors="coerce")
    for field in ("units_sold", "on_hand", "store_size", "selling_price"):
        if field in data.columns:
            data[field] = pd.to_numeric(data[field], errors="coerce")
    if "promo_active" in data.columns:
        data["promo_active"] = data["promo_active"].map(
            lambda value: value if isinstance(value, bool) else str(value).strip().lower() in {"1", "true", "yes", "y"}
        )
    if "is_phantom" in data.columns:
        data["is_phantom"] = data["is_phantom"].map(
            lambda value: value if isinstance(value, bool) else str(value).strip().lower() in {"1", "true", "yes", "y"}
        )
    for field in ("store_id", "sku_id", "store_format", "city_tier", "sku_name", "category"):
        if field in data.columns:
            data[field] = data[field].astype("string").str.strip()
    return data

def load_all_tables(schema_path, project_root=None):
    """Load all available configured tables; sales and inventory are required."""
    schema_path = Path(schema_path)
    root = Path(project_root) if project_root else schema_path.resolve().parent.parent
    schema = read_schema(schema_path)
    tables = {}
    for name, required in REQUIRED_FIELDS.items():
        tables[name] = load_mapped_table(root, name, schema.get(name), required)
    for name, fields in OPTIONAL_FIELDS.items():
        if name in ("sales", "inventory"):
            continue
        tables[name] = load_mapped_table(root, name, schema.get(name), fields) if schema.get(name) else None
    return tables
