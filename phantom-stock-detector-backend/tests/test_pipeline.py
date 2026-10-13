import json
import pandas as pd
from run_pipeline import run_pipeline

def test_pipeline_writes_required_csv_columns(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    dates = pd.date_range("2026-01-01", periods=10)
    rows = []
    for i, date in enumerate(dates):
        rows.append({"date": str(date.date()), "store_id": "S1", "sku_id": "X1", "units_sold": 2 if i < 7 else 0})
    pd.DataFrame(rows).to_csv(data_dir / "sales.csv", index=False)
    inventory = [{"date": str(d.date()), "store_id": "S1", "sku_id": "X1", "on_hand": 10} for d in dates]
    pd.DataFrame(inventory).to_csv(data_dir / "inventory.csv", index=False)
    schema = {
        "sales": {"file": str(data_dir / "sales.csv"), "date": "date", "store_id": "store_id", "sku_id": "sku_id", "units_sold": "units_sold"},
        "inventory": {"file": str(data_dir / "inventory.csv"), "date": "date", "store_id": "store_id", "sku_id": "sku_id", "on_hand": "on_hand"}
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema))
    out = tmp_path / "output"
    run_pipeline(schema_path, out, top_k=20, evaluate=False, verbose=False)
    result = pd.read_csv(out / "daily_alerts.csv")
    assert "phantom_score" in result.columns
    assert "reason" in result.columns
    assert (out / "alert_history.csv").exists()
    assert (out / "summary_metrics.json").exists()
