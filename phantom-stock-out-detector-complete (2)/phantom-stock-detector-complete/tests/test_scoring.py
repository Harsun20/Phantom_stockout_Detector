import pandas as pd
from src.scoring import score_features, rank_alerts

def sample_df(n=25):
    return pd.DataFrame({
        "date":pd.to_datetime(["2026-01-10"]*n),
        "store_id":["S1"]*n,
        "sku_id":[f"K{i:03d}" for i in range(n)],
        "on_hand":[10]*n,
        "zero_sales_streak":[6]*n,
        "expected_daily_sales":[2.0]*n,
        "slow_mover":[False]*n,
        "inventory_days_unchanged":[8]*n,
        "peer_store_sales":[1.0]*n,
        "promo_active":[False]*n,
    })

def test_score_is_between_zero_and_100():
    scored = score_features(sample_df())
    assert scored["phantom_score"].between(0,100).all()

def test_slow_movers_are_not_candidates():
    df = sample_df(1)
    df["expected_daily_sales"] = 0.1
    df["slow_mover"] = True
    scored = score_features(df)
    assert not bool(scored.loc[0, "candidate"])

def test_top20_limit_is_respected():
    scored = score_features(sample_df(25))
    alerts = rank_alerts(scored, top_k=20)
    assert len(alerts) == 20
    assert alerts["rank_in_store"].max() == 20
