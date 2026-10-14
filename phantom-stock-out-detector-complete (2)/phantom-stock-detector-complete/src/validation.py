"""Data quality checks and readable validation summaries."""
import pandas as pd

KEYS = ["date", "store_id", "sku_id"]

def validate_tables(tables, verbose=True):
    """Validate required input tables and return cleaned sales/inventory tables."""
    cleaned = {}
    for name, numeric in (("sales", "units_sold"), ("inventory", "on_hand")):
        df = tables.get(name)
        if df is None:
            raise ValueError(f"Required table '{name}' was not loaded.")
        missing = [c for c in KEYS + [numeric] if c not in df.columns]
        if missing:
            raise ValueError(f"{name} is missing required standardized columns: {missing}")
        before = len(df)
        df = df.copy()
        df = df.dropna(subset=KEYS + [numeric])
        df = df[(df["store_id"].astype(str).str.strip() != "") & (df["sku_id"].astype(str).str.strip() != "")]
        duplicates = int(df.duplicated(KEYS, keep=False).sum())
        if duplicates:
            duplicate_keys = df.loc[df.duplicated(KEYS, keep=False), KEYS].drop_duplicates().head(5).to_dict("records")
            raise ValueError(f"{name} contains duplicate date-store-sku rows ({duplicates} rows). Examples: {duplicate_keys}")
        if name == "sales" and (df[numeric] < 0).any():
            raise ValueError("sales contains negative units_sold values; correct returns/refunds before running this prototype.")
        if name == "inventory" and (df[numeric] < 0).any():
            raise ValueError("inventory contains negative on_hand values.")
        cleaned[name] = df
        if verbose:
            date_range = "n/a"
            if "date" in df and not df.empty:
                date_range = f"{df['date'].min().date()} to {df['date'].max().date()}"
            print(f"{name}: {len(df)} valid rows (excluded {before-len(df)}), date range {date_range}")
    sales_keys = cleaned["sales"][KEYS].drop_duplicates()
    inventory_keys = cleaned["inventory"][KEYS].drop_duplicates()
    overlap = sales_keys.merge(inventory_keys, on=KEYS, how="inner")
    if overlap.empty:
        raise ValueError("Sales and inventory have no overlapping date-store-sku keys.")
    if verbose:
        print(f"Join coverage: {len(overlap)} overlapping keys; sales keys={len(sales_keys)}, inventory keys={len(inventory_keys)}")
    return cleaned

def validation_summary(tables, merged):
    """Return compact row-count and coverage details for summary JSON."""
    sales = tables["sales"]
    inventory = tables["inventory"]
    return {
        "sales_rows": int(len(sales)),
        "inventory_rows": int(len(inventory)),
        "merged_rows": int(len(merged)),
        "sales_date_range": [str(sales["date"].min().date()), str(sales["date"].max().date())] if len(sales) else [],
        "inventory_date_range": [str(inventory["date"].min().date()), str(inventory["date"].max().date())] if len(inventory) else [],
    }
