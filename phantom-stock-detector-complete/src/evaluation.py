"""Synthetic ground-truth evaluation helpers."""
import pandas as pd

def evaluate_top20(alerts, ground_truth):
    """Calculate precision@20 per store-date and the mean; use only for evaluation."""
    if ground_truth is None or ground_truth.empty:
        return {"available": False, "note": "No ground-truth data available; core pipeline does not require it."}
    truth = ground_truth[["date", "store_id", "sku_id", "is_phantom"]].copy()
    truth["date"] = pd.to_datetime(truth["date"], errors="coerce")
    truth["is_phantom"] = truth["is_phantom"].astype(bool)
    top = alerts.copy()
    if top.empty:
        return {
            "available": True, "mean_precision_at_20": 0.0, "total_true_positives_in_top20": 0,
            "groups_evaluated": 0, "note": "Synthetic-demo-only metric; no alert rows were produced."
        }
    joined = top.merge(truth, on=["date", "store_id", "sku_id"], how="left")
    joined["is_phantom"] = joined["is_phantom"].fillna(False)
    rows = []
    for (date, store), group in joined.groupby(["date", "store_id"]):
        tp = int(group["is_phantom"].sum())
        rows.append({"date": str(date.date()), "store_id": str(store), "precision_at_20": tp / 20.0, "true_positives": tp})
    mean_precision = sum(r["precision_at_20"] for r in rows) / len(rows) if rows else 0.0
    return {
        "available": True,
        "mean_precision_at_20": round(mean_precision, 4),
        "total_true_positives_in_top20": int(sum(r["true_positives"] for r in rows)),
        "groups_evaluated": len(rows),
        "by_store_date": rows,
        "note": "Synthetic-demo-only evaluation. These results are not real-world performance claims."
    }
