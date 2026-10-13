"""Synthetic ground-truth evaluation; never used by the scoring model."""
import pandas as pd

def evaluate_top_k(alerts, ground_truth, top_k=20):
    """Compute precision@K for each store-date group and aggregate mean precision."""
    if ground_truth is None or ground_truth.empty:
        return {"available": False, "note": "No ground-truth file supplied; evaluation skipped."}
    required = {"date", "store_id", "sku_id", "is_phantom"}
    if not required.issubset(ground_truth.columns):
        return {"available": False, "note": f"Ground truth missing columns: {sorted(required - set(ground_truth.columns))}"}
    truth = ground_truth.copy()
    truth["date"] = pd.to_datetime(truth["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    truth["is_phantom"] = truth["is_phantom"].astype(str).str.lower().isin(["1", "true", "yes"])
    alert_frame = alerts.sort_values(["date", "store_id", "rank_in_store"]).copy()
    alert_frame["date"] = pd.to_datetime(alert_frame["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    precisions, tp = [], 0
    groups = truth.groupby(["date", "store_id"])
    for key, group in groups:
        actual = set(group.loc[group["is_phantom"], "sku_id"].astype(str))
        selected = alert_frame[(alert_frame["date"] == str(key[0])) & (alert_frame["store_id"].astype(str) == str(key[1]))].head(top_k)
        hits = int(selected["sku_id"].astype(str).isin(actual).sum())
        precisions.append(hits / max(len(selected), 1))
        tp += hits
    return {
        "available": True,
        "evaluation_scope": "Synthetic demo only; these metrics are not real-world performance claims.",
        "precision_at_k": top_k,
        "mean_precision_at_k_by_store_date": round(sum(precisions) / len(precisions), 4) if precisions else 0.0,
        "total_true_positives_in_top_k": tp,
        "evaluated_store_date_groups": len(precisions),
    }
