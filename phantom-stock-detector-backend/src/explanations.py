"""Generate concise, data-backed alert reasons."""
def make_reason(row):
    """Create a one-line explanation using only values present on the row."""
    stock = f"{row.get('on_hand', 0):g} recorded units"
    streak = int(row.get("zero_sales_streak", 0))
    demand = float(row.get("expected_daily_sales", 0) or 0)
    reason = f"{stock}, zero sales for {streak} consecutive day(s), expected demand {demand:.2f} units/day"
    peer = row.get("peer_store_sales")
    if peer is not None and peer == peer:
        reason += f", comparable stores sold {float(peer):.2f} units/day"
    if bool(row.get("promo_active", False)):
        reason += ", promotion active"
    if row.get("alert_type") == "possible_wrong_shelf":
        reason += "; unchanged inventory may indicate a shelf-location or planogram issue"
    elif row.get("alert_type") == "likely_phantom_stockout":
        reason += "; positive recorded stock may not be available on the shelf"
    else:
        reason += "; continue monitoring before escalating"
    return reason + "."
