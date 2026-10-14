"""Illustrative revenue-at-risk scenario calculations."""
import json
from pathlib import Path
import pandas as pd

def write_recovery_estimate(alerts, output_path):
    """Write an explicitly illustrative estimate; it is not measured recovery."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if alerts.empty:
        payload = {
            "label": "Illustrative scenario estimate, not measured recovery",
            "alert_rows": 0,
            "expected_lost_units_proxy": 0.0,
            "potential_revenue_at_risk": 0.0,
            "assumptions": ["Expected lost units proxy = expected_daily_sales × zero_sales_streak."],
            "note": "Demo data results are not real-world performance claims."
        }
    elif "selling_price" not in alerts.columns or alerts["selling_price"].notna().sum() == 0:
        payload = {
            "label": "Illustrative scenario estimate, not measured recovery",
            "alert_rows": int(len(alerts)),
            "expected_lost_units_proxy": round(float(alerts["expected_lost_units"].fillna(0).sum()), 2),
            "potential_revenue_at_risk": None,
            "note": "Rupee recovery estimation requires selling price or margin data. This is a scenario estimate, not measured recovery."
        }
    else:
        usable = alerts.dropna(subset=["selling_price"])
        revenue = (usable["expected_lost_units"].fillna(0) * usable["selling_price"]).sum()
        payload = {
            "label": "Illustrative scenario estimate, not measured recovery",
            "alert_rows": int(len(alerts)),
            "expected_lost_units_proxy": round(float(alerts["expected_lost_units"].fillna(0).sum()), 2),
            "potential_revenue_at_risk": round(float(revenue), 2),
            "currency": "INR",
            "assumptions": [
                "Expected lost units proxy = expected_daily_sales × zero_sales_streak.",
                "Potential revenue at risk = expected lost units proxy × listed selling price.",
                "This does not establish that all estimated units would have sold or been recovered."
            ],
            "note": "Demo data results are not real-world performance claims."
        }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
