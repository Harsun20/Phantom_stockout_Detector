"""Central place for configurable business thresholds and scoring weights."""

ZERO_STREAK_MIN = 3
MIN_EXPECTED_DAILY_SALES = 0.50
SLOW_MOVER_THRESHOLD = 0.20
ROLLING_WINDOW_DAYS = 28
ROLLING_MIN_PERIODS = 7
INVENTORY_UNCHANGED_DAYS = 3
MAX_ALERTS_PER_STORE_DAY = 20

# Weights are normalized to a 0-100 score. Change these to tune the prototype.
SCORE_WEIGHTS = {
    "positive_stock": 15.0,
    "zero_streak": 25.0,
    "historical_demand": 20.0,
    "inventory_unchanged": 10.0,
    "peer_demand": 15.0,
    "promotion": 5.0,
    "slow_mover_penalty": 15.0,
}

def threshold_summary():
    """Return the settings that should be recorded in the run summary."""
    return {
        "zero_streak_min": ZERO_STREAK_MIN,
        "min_expected_daily_sales": MIN_EXPECTED_DAILY_SALES,
        "slow_mover_threshold": SLOW_MOVER_THRESHOLD,
        "rolling_window_days": ROLLING_WINDOW_DAYS,
        "rolling_min_periods": ROLLING_MIN_PERIODS,
        "inventory_unchanged_days": INVENTORY_UNCHANGED_DAYS,
        "max_alerts_per_store_day": MAX_ALERTS_PER_STORE_DAY,
        "score_weights": SCORE_WEIGHTS,
    }
