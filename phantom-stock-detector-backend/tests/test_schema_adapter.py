import json
import pandas as pd
from src.schema_adapter import load_standardized_data

def test_schema_maps_different_source_column_names(tmp_path, monkeypatch):
    pd.DataFrame({"business_date": ["2026-01-01"], "shop": [" S1 "], "item": [" X1 "], "qty": [2]}).to_csv(tmp_path / "s.csv", index=False)
    pd.DataFrame({"snapshot": ["2026-01-01"], "shop": ["S1"], "item": ["X1"], "stock": [4]}).to_csv(tmp_path / "i.csv", index=False)
    schema = {
        "sales": {"file": str(tmp_path / "s.csv"), "date": "business_date", "store_id": "shop", "sku_id": "item", "units_sold": "qty"},
        "inventory": {"file": str(tmp_path / "i.csv"), "date": "snapshot", "store_id": "shop", "sku_id": "item", "on_hand": "stock"}
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema))
    data = load_standardized_data(schema_path)
    assert list(data["sales"].columns) == ["date", "store_id", "sku_id", "units_sold"]
    assert data["sales"].iloc[0]["store_id"] == "S1"
    assert data["inventory"].iloc[0]["on_hand"] == 4
