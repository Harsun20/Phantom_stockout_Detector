"""Generate concise, data-backed explanations for each candidate alert."""
import pandas as pd

def explain_row(row):
    """Build a one-line explanation using values actually present in the feature row."""
    on_hand = int(row["on_hand"]) if pd.notna(row.get("on_hand")) else 0
    streak = int(row["zero_sales_streak"]) if pd.notna(row.get("zero_sales_streak")) else 0
    demand = float(row["expected_daily_sales"]) if pd.notna(row.get("expected_daily_sales")) else 0.0
    peer = row.get("peer_store_sales")
    alert_type = row.get("alert_type", "monitor")
    if alert_type == "possible_wrong_shelf":
        reason = f"Possible wrong-shelf pattern: {on_hand} recorded units, zero sales for {streak} days, and expected demand of {demand:.2f} units/day."
    elif alert_type == "likely_phantom_stockout":
        reason = f"{on_hand} recorded units remain despite {streak} zero-sales days; historical demand is {demand:.2f} units/day"
        if pd.notna(peer):
            reason += f", while comparable stores averaged {float(peer):.2f} units/day"
        reason += "."
    else:
        reason = f"Monitor: {on_hand} recorded units and {streak} consecutive zero-sales days; expected demand is {demand:.2f} units/day."
    if bool(row.get("promo_active", False)):
        reason = reason.rstrip(".") + "; promotion is active."
    return reason

def add_explanations(df):
    """Add a reason column to a DataFrame."""
    result = df.copy()
    result["reason"] = result.apply(explain_row, axis=1)
    return result
