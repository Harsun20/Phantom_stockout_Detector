"""Run the full CSV-to-alert pipeline from the terminal."""
import argparse
import json
import time
from pathlib import Path
import pandas as pd
from src.data_loader import load_data
from src.validation import validate_data
from src.feature_engineering import build_features
from src.scoring import score_features, rank_alerts
from src.explanations import make_reason
from src.recovery_estimate import build_recovery_estimate
from src.evaluation import evaluate_top_k
from src import config

OUTPUT_COLUMNS = [
    "date", "store_id", "rank_in_store", "sku_id", "sku_name", "category",
    "phantom_score", "confidence", "alert_type", "recommended_action", "on_hand",
    "units_sold", "zero_sales_streak", "expected_daily_sales", "peer_store_sales",
    "promo_active", "inventory_days_unchanged", "expected_lost_units", "reason"
]
HISTORY_COLUMNS = [
    "date", "store_id", "sku_id", "units_sold", "on_hand", "expected_daily_sales",
    "peer_store_sales", "promo_active", "phantom_score", "candidate"
]

def run_pipeline(schema_path, output_dir="output", top_k=20, evaluate=False, verbose=False):
    """Execute validation, feature engineering, scoring, ranking, and output writing."""
    start = time.perf_counter()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    data = load_data(schema_path)
    data = validate_data(data, verbose=verbose)
    features = build_features(data)
    scored = score_features(features)
    alerts = rank_alerts(scored, top_k=top_k)
    alerts["reason"] = alerts.apply(make_reason, axis=1)
    for col in OUTPUT_COLUMNS:
        if col not in alerts.columns:
            alerts[col] = pd.NA
    alerts = alerts[OUTPUT_COLUMNS].copy()
    history = scored.copy()
    for col in HISTORY_COLUMNS:
        if col not in history.columns:
            history[col] = pd.NA
    history = history[HISTORY_COLUMNS].copy()
    for frame in (alerts, history):
        if "date" in frame:
            frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    alerts.to_csv(output_path / "daily_alerts.csv", index=False)
    history.to_csv(output_path / "alert_history.csv", index=False)

    date_values = pd.to_datetime(features["date"], errors="coerce").dropna()
    summary = {
        "input_row_counts": {
            "sales": int(len(data["sales"])), "inventory": int(len(data["inventory"])),
            "promotions": int(len(data["promotions"])) if data.get("promotions") is not None else 0,
            "stores": int(len(data["stores"])) if data.get("stores") is not None else 0,
            "products": int(len(data["products"])) if data.get("products") is not None else 0,
        },
        "merged_row_count": int(len(features)),
        "total_candidate_count": int(scored["candidate"].sum()),
        "total_top_k_alert_count": int(len(alerts)),
        "top_k_per_store_date": int(top_k),
        "number_of_stores": int(features["store_id"].nunique()),
        "date_range": {"start": str(date_values.min().date()), "end": str(date_values.max().date())} if not date_values.empty else None,
        "threshold_settings": {
            "slow_mover_threshold": config.SLOW_MOVER_THRESHOLD,
            "min_expected_demand": config.MIN_EXPECTED_DEMAND,
            "min_zero_streak": config.MIN_ZERO_STREAK,
            "rolling_window_days": config.ROLLING_WINDOW_DAYS,
            "weights": config.WEIGHTS,
        },
        "runtime_seconds": round(time.perf_counter() - start, 3),
        "note": "Demo data results are not real-world performance claims.",
    }
    (output_path / "summary_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    recovery = build_recovery_estimate(alerts, products_available=data.get("products") is not None)
    (output_path / "recovery_estimate.json").write_text(json.dumps(recovery, indent=2), encoding="utf-8")
    if evaluate:
        evaluation = evaluate_top_k(alerts, data.get("ground_truth"), top_k=top_k)
        (output_path / "evaluation_metrics.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    if verbose:
        print(f"Pipeline complete: {len(features)} merged rows, {int(scored['candidate'].sum())} candidates, {len(alerts)} ranked alerts.")
        print(f"Output directory: {output_path.resolve()}")
    return summary

def main():
    parser = argparse.ArgumentParser(description="Detect possible phantom stock-outs from sales and inventory CSVs.")
    parser.add_argument("--schema", default="config/schema.demo.json", help="Path to schema mapping JSON")
    parser.add_argument("--top-k", type=int, default=config.DEFAULT_TOP_K, help="Maximum alerts per store/date")
    parser.add_argument("--output-dir", default="output", help="Directory for generated outputs")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate using configured ground truth, if available")
    parser.add_argument("--verbose", action="store_true", help="Print validation and completion details")
    args = parser.parse_args()
    try:
        summary = run_pipeline(args.schema, args.output_dir, args.top_k, args.evaluate, args.verbose)
        print("Pipeline completed successfully.")
        print(f"Merged rows: {summary['merged_row_count']}; candidate alerts: {summary['total_candidate_count']}; top alerts written: {summary['total_top_k_alert_count']}")
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit(f"Pipeline could not complete: {exc}") from None

if __name__ == "__main__":
    main()
