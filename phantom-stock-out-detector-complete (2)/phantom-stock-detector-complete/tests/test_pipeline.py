import json
import pandas as pd
from run_pipeline import run

def test_pipeline_outputs_required_columns(tmp_path):
    data = tmp_path / "data"
    out = tmp_path / "out"
    data.mkdir()
    dates = pd.date_range("2026-01-01", periods=12)
    sales = pd.DataFrame({"d":dates,"s":["S1"]*12,"k":["K1"]*12,"qty":[2,2,2,2,2,2,0,0,0,0,0,0]})
    inventory = pd.DataFrame({"d":dates,"s":["S1"]*12,"k":["K1"]*12,"stock":[10]*12})
    sales.to_csv(data/"sales.csv",index=False)
    inventory.to_csv(data/"inventory.csv",index=False)
    schema = {
        "sales":{"file":str(data/"sales.csv"),"date":"d","store_id":"s","sku_id":"k","units_sold":"qty"},
        "inventory":{"file":str(data/"inventory.csv"),"date":"d","store_id":"s","sku_id":"k","on_hand":"stock"}
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    run(str(schema_path), str(out), top_k=20)
    alerts = pd.read_csv(out/"daily_alerts.csv")
    for col in ["date","store_id","rank_in_store","sku_id","phantom_score","reason","recommended_action"]:
        assert col in alerts.columns
    assert (out/"alert_history.csv").exists()
    assert (out/"summary_metrics.json").exists()
    assert (out/"recovery_estimate.json").exists()
