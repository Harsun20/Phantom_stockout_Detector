import json
import pandas as pd
from src.schema_adapter import load_mapped_table

def test_maps_differently_named_columns(tmp_path):
    csv_path = tmp_path / "sales.csv"
    pd.DataFrame({"business_day":["2026-01-01"],"location":[" S001 "],"item":["SKU1"],"qty":[2]}).to_csv(csv_path, index=False)
    cfg = {"file": str(csv_path), "date":"business_day", "store_id":"location", "sku_id":"item", "units_sold":"qty"}
    df = load_mapped_table(tmp_path, "sales", cfg, ["date","store_id","sku_id","units_sold"])
    assert list(df.columns) == ["date","store_id","sku_id","units_sold"]
    assert df.loc[0, "store_id"] == "S001"
    assert df.loc[0, "units_sold"] == 2
