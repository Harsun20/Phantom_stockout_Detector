"""Centralized, easy-to-adjust pipeline settings."""
DEFAULT_TOP_K = 20
ROLLING_WINDOW_DAYS = 28
ROLLING_MIN_PERIODS = 7
SLOW_MOVER_THRESHOLD = 0.20
MIN_EXPECTED_DEMAND = 0.50
MIN_ZERO_STREAK = 3
HIGH_CONFIDENCE_SCORE = 75
MEDIUM_CONFIDENCE_SCORE = 45

# Weighted score components. The final score is clipped to 0..100.
WEIGHTS = {
    "positive_stock": 15,
    "zero_streak": 25,
    "expected_demand": 20,
    "inventory_unchanged": 10,
    "peer_demand": 15,
    "promotion": 5,
    "slow_mover_penalty": 20,
}
