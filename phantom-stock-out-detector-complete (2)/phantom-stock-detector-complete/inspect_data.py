"""Inspect every CSV referenced by a schema configuration."""
import argparse
from pathlib import Path
import pandas as pd
from src.schema_adapter import read_schema

ROOT = Path(__file__).resolve().parent

def inspect(schema_path):
    """Print useful diagnostics for each configured CSV file."""
    schema = read_schema(schema_path)
    schema_file = Path(schema_path)
    root = schema_file.resolve().parent.parent
    for table_name, config in schema.items():
        if not isinstance(config, dict) or not config.get("file"):
            continue
        path = Path(config["file"])
        if not path.is_absolute():
            path = root / path
        print(f"\n{'='*72}\nTable: {table_name}\nFile: {path}")
        if not path.exists():
            print("File does not exist (optional files may be omitted).")
            continue
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            print(f"Could not read file: {exc}")
            continue
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print("\nDtypes:\n", df.dtypes.to_string())
        print("\nFirst 5 rows:\n", df.head().to_string(index=False))
        print("\nMissing values:\n", df.isna().sum().to_string())
        date_col = config.get("date")
        if date_col and date_col in df.columns:
            dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
            if not dates.empty:
                print(f"\nDate range: {dates.min().date()} to {dates.max().date()}")
            else:
                print("\nDate range: no valid dates found")
    return 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", default="config/schema.demo.json")
    args = parser.parse_args()
    try:
        inspect(args.schema)
    except ValueError as exc:
        parser.exit(2, f"Error: {exc}\n")

if __name__ == "__main__":
    main()
