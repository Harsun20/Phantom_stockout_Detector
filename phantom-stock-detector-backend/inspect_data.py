"""Inspect CSVs referenced by a schema file."""
import argparse
from pathlib import Path
import pandas as pd
from src.schema_adapter import read_schema

def main():
    parser = argparse.ArgumentParser(description="Inspect CSV input files referenced by a schema.")
    parser.add_argument("--schema", default="config/schema.demo.json")
    args = parser.parse_args()
    schema = read_schema(args.schema)
    for section, mapping in schema.items():
        if not isinstance(mapping, dict) or not mapping.get("file"):
            continue
        path = Path(mapping["file"])
        if not path.is_absolute():
            path = Path.cwd() / path
        print(f"\n=== {section}: {path} ===")
        if not path.exists():
            print("File not found (optional files may be absent).")
            continue
        try:
            frame = pd.read_csv(path)
        except Exception as exc:
            print(f"Could not read file: {exc}")
            continue
        print(f"Shape: {frame.shape}")
        print(f"Columns: {list(frame.columns)}")
        print("Data types:")
        print(frame.dtypes.to_string())
        print("First 5 rows:")
        print(frame.head().to_string(index=False))
        print("Missing values:")
        print(frame.isna().sum().to_string())
        date_source = mapping.get("date")
        if date_source and date_source in frame:
            parsed = pd.to_datetime(frame[date_source], errors="coerce").dropna()
            if not parsed.empty:
                print(f"Date range: {parsed.min().date()} to {parsed.max().date()}")

if __name__ == "__main__":
    main()
