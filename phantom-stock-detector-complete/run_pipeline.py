"""Run the complete local Phantom Stock-Out Detector pipeline."""
import argparse
import json
import time
from pathlib import Path
import pandas as pd
from src import config
from src.data_loader import load_data
from src.validation import validate_tables, validation_summary
from src.feature_engineering import build_features
from src.scoring import score_features, rank_alerts
from src.explanations import add_explanations
from src.recovery_estimate import write_recovery_estimate
from src.evaluation import evaluate_top20

ROOT = Path(__file__).resolve().parent

def json_safe(value):
    """Convert pandas/numpy values into JSON-compatible Python values."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        return value.item()
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value

def run(schema_path, output_dir="output", top_k=20, evaluate=False, verbose=False):
    """Execute the pipeline and write all requested outputs."""
    start = time.perf_counter()
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.mkdir(parents=True, exist_ok=True)
    tables = load_data(schema_path, project_root=ROOT)
    cleaned_tables = validate_tables(tables, verbose=True)
    tables["sales"] = cleaned_tables["sales"]
    tables["inventory"] = cleaned_tables["inventory"]
    features = build_features(tables)
    scored = score_features(features)
    scored = add_explanations(scored)
    alerts = rank_alerts(scored, top_k=top_k)
    alert_columns = [
        "date","store_id","rank_in_store","sku_id","sku_name","category","phantom_score","confidence",
        "alert_type","recommended_action","on_hand","units_sold","zero_sales_streak","expected_daily_sales",
        "peer_store_sales","promo_active","inventory_days_unchanged","expected_lost_units","reason"
    ]
    for col in alert_columns:
        if col not in alerts.columns:
            alerts[col] = pd.NA
    alerts_out = alerts[alert_columns].copy()
    if not alerts_out.empty:
        alerts_out["date"] = alerts_out["date"].dt.strftime("%Y-%m-%d")
    alerts_out.to_csv(output_path / "daily_alerts.csv", index=False)

    history = scored[[
        "date","store_id","sku_id","units_sold","on_hand","expected_daily_sales","peer_store_sales",
        "promo_active","phantom_score","candidate"
    ]].copy()
    history["date"] = history["date"].dt.strftime("%Y-%m-%d")
    history.to_csv(output_path / "alert_history.csv", index=False)

    counts = validation_summary(tables, features)
    date_min, date_max = features["date"].min(), features["date"].max()
    summary = {
        "input_row_counts": {"sales": counts["sales_rows"], "inventory": counts["inventory_rows"]},
        "merged_row_count": int(len(features)),
        "total_candidate_count": int(scored["candidate"].sum()),
        "total_top_20_alert_count": int(len(alerts_out)),
        "number_of_stores": int(features["store_id"].nunique()),
        "date_range": {"start": str(date_min.date()), "end": str(date_max.date())},
        "threshold_settings": config.threshold_summary(),
        "runtime_seconds": round(time.perf_counter() - start, 3),
        "note": "Demo data results are not real-world performance claims."
    }
    (output_path / "summary_metrics.json").write_text(json.dumps(json_safe(summary), indent=2), encoding="utf-8")
    write_recovery_estimate(alerts, output_path / "recovery_estimate.json")

    evaluation = None
    ground_truth = tables.get("ground_truth")
    if evaluate and ground_truth is not None:
        evaluation = evaluate_top20(alerts, ground_truth)
        (output_path / "evaluation.json").write_text(json.dumps(json_safe(evaluation), indent=2), encoding="utf-8")
    elif evaluate:
        evaluation = {"available": False, "note": "No ground-truth file was configured; core pipeline completed."}
        (output_path / "evaluation.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")

    # Update runtime after all work has completed.
    summary["runtime_seconds"] = round(time.perf_counter() - start, 3)
    (output_path / "summary_metrics.json").write_text(json.dumps(json_safe(summary), indent=2), encoding="utf-8")
    print("\nPipeline completed successfully.")
    print(f"Merged rows: {len(features)} | candidates: {int(scored['candidate'].sum())} | top-K alerts: {len(alerts_out)}")
    print(f"Outputs: {output_path}")
    if evaluation:
        print(f"Evaluation: {evaluation.get('note', 'completed')}")
    if verbose:
        print("\nTop alerts preview:")
        print(alerts_out.head(10).to_string(index=False))
    return {"features": features, "scored": scored, "alerts": alerts_out, "summary": summary}

def main():
    parser = argparse.ArgumentParser(description="Detect possible phantom stock-outs from CSV data.")
    parser.add_argument("--schema", default="config/schema.demo.json", help="Path to schema JSON.")
    parser.add_argument("--top-k", type=int, default=config.MAX_ALERTS_PER_STORE_DAY, help="Maximum alerts per store per date.")
    parser.add_argument("--output-dir", default="output", help="Output folder.")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate using configured synthetic ground truth, if present.")
    parser.add_argument("--verbose", action="store_true", help="Print a preview of alerts.")
    args = parser.parse_args()
    try:
        run(args.schema, args.output_dir, args.top_k, args.evaluate, args.verbose)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        parser.exit(2, f"Error: {exc}\n")

if __name__ == "__main__":
    main()
