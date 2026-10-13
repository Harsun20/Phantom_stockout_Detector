import pandas as pd
from src.scoring import score_features, rank_alerts

def base_frame(n=1):
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01"] * n), "store_id": ["S1"] * n,
        "sku_id": [f"X{i}" for i in range(n)], "on_hand": [8] * n,
        "zero_sales_streak": [5] * n, "expected_daily_sales": [1.5] * n,
        "inventory_days_unchanged": [6] * n, "peer_store_sales": [1.0] * n,
        "promo_active": [False] * n, "slow_mover": [False] * n,
    })

def test_slow_movers_not_high_priority_candidates():
    frame = base_frame()
    frame["expected_daily_sales"] = 0.1
    frame["slow_mover"] = True
    result = score_features(frame)
    assert not bool(result.iloc[0]["candidate"])
    assert result.iloc[0]["alert_type"] == "monitor"

def test_score_is_between_zero_and_100():
    result = score_features(base_frame(3))
    assert result["phantom_score"].between(0, 100).all()

def test_top_k_limit_is_respected():
    frame = base_frame(25)
    result = score_features(frame)
    alerts = rank_alerts(result, top_k=20)
    assert len(alerts) <= 20
    assert alerts["rank_in_store"].max() <= 20
