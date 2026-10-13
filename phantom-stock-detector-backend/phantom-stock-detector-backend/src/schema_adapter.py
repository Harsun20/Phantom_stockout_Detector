"""Load CSV files described by a schema JSON and standardize column names."""
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
}

def read_schema(schema_path):
    """Read and return a schema JSON object."""
    path = Path(schema_path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Schema file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in schema file {path}: {exc}") from exc

def _load_one(section, mapping, base_dir):
    """Read one configured CSV and rename mapped source columns to standard names."""
    if not isinstance(mapping, dict) or not mapping.get("file"):
        if section in REQUIRED_FIELDS:
            raise ValueError(f"Schema section '{section}' must include a CSV 'file' path.")
        return None
    path = Path(mapping["file"])
    if not path.is_absolute():
        path = base_dir / path
    if not path.exists():
        if section in REQUIRED_FIELDS:
            raise ValueError(f"Required {section} CSV file not found: {path}")
        return None
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        raise ValueError(f"Could not read {section} CSV '{path}': {exc}") from exc

    fields = REQUIRED_FIELDS.get(section, OPTIONAL_FIELDS.get(section, []))
    rename = {}
    missing = []
    for standard_name in fields:
        source_name = mapping.get(standard_name)
        if source_name is None:
            if section in REQUIRED_FIELDS:
                missing.append(f"schema mapping for '{standard_name}'")
            continue
        if source_name not in frame.columns:
            missing.append(f"column '{source_name}'")
        else:
            rename[source_name] = standard_name
    if missing:
        if section in REQUIRED_FIELDS:
            raise ValueError(f"{section} file '{path}' is missing: {', '.join(missing)}")
        return None
    frame = frame.rename(columns=rename)
    keep = [name for name in fields if name in frame.columns]
    frame = frame[keep].copy()
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    for col in ("units_sold", "on_hand", "store_size", "selling_price"):
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in ("store_id", "sku_id"):
        if col in frame.columns:
            frame[col] = frame[col].astype("string").str.strip()
    if "promo_active" in frame.columns:
        frame["promo_active"] = frame["promo_active"].map(
            lambda value: str(value).strip().lower() in {"1", "true", "yes", "y", "active"}
            if pd.notna(value) else False
        )
    return frame

def load_standardized_data(schema_path):
    """Load required sales/inventory and any available optional tables."""
    schema_path = Path(schema_path)
    schema = read_schema(schema_path)
    base_dir = Path.cwd()
    # Resolve relative file paths from the project root, not from config/.
    result = {}
    for section in ["sales", "inventory", "promotions", "stores", "products", "ground_truth"]:
        mapping = schema.get(section)
        if section == "ground_truth":
            if not mapping or not mapping.get("file"):
                result[section] = None
                continue
            path = Path(mapping["file"])
            if not path.is_absolute():
                path = base_dir / path
            if not path.exists():
                result[section] = None
                continue
            try:
                gt = pd.read_csv(path)
                rename = {source: standard for standard, source in mapping.items()
                          if standard != "file" and source in gt.columns}
                gt = gt.rename(columns=rename)
                if "date" in gt:
                    gt["date"] = pd.to_datetime(gt["date"], errors="coerce").dt.normalize()
                if "store_id" in gt:
                    gt["store_id"] = gt["store_id"].astype("string").str.strip()
                if "sku_id" in gt:
                    gt["sku_id"] = gt["sku_id"].astype("string").str.strip()
                result[section] = gt
            except Exception as exc:
                raise ValueError(f"Could not read ground_truth file '{path}': {exc}") from exc
            continue
        result[section] = _load_one(section, mapping, base_dir)
    return result
