"""Create a transparent, illustrative revenue-at-risk scenario."""
def build_recovery_estimate(alerts, products_available=True):
    """Estimate potential revenue at risk; this is not measured recovered revenue."""
    result = {
        "estimate_type": "illustrative scenario estimate",
        "assumption": "Expected lost units are a simple proxy (expected daily demand × zero-sales streak); it is not measured lost sales or recovered revenue.",
        "alert_count": int(len(alerts)),
        "total_expected_lost_units": round(float(alerts.get("expected_lost_units", []).sum()), 2) if len(alerts) else 0.0,
    }
    if products_available and len(alerts) and "selling_price" in alerts.columns:
        priced = alerts.dropna(subset=["selling_price"]).copy()
        priced["scenario_revenue_at_risk"] = priced["expected_lost_units"] * priced["selling_price"]
        result["priced_alert_count"] = int(len(priced))
        result["potential_revenue_at_risk_inr"] = round(float(priced["scenario_revenue_at_risk"].sum()), 2)
        result["currency"] = "INR"
    else:
        result["note"] = "Rupee recovery estimates require selling_price or margin data. No currency estimate was calculated."
    return result
