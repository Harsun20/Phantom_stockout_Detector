"""Transparent risk scoring and ranked daily alerts."""
import numpy as np
import pandas as pd
from . import config

def _clip01(value):
    return float(max(0.0, min(1.0, value))) if pd.notna(value) else 0.0

def score_features(features):
    """Add a 0-100 phantom score, candidate flag, confidence, alert type and action."""
    df = features.copy()
    w = config.SCORE_WEIGHTS
    positive_stock = (df["on_hand"] > 0).astype(float)
    streak_component = df["zero_sales_streak"].map(lambda x: _clip01(x / max(config.ZERO_STREAK_MIN * 2, 1)))
    demand_component = df["expected_daily_sales"].map(lambda x: _clip01(x / 3.0))
    unchanged_component = df["inventory_days_unchanged"].map(lambda x: _clip01(x / max(config.INVENTORY_UNCHANGED_DAYS * 2, 1)))
    peer_component = df["peer_store_sales"].map(lambda x: _clip01(x / 2.0) if pd.notna(x) else 0.0)
    promo_component = df["promo_active"].astype(float)
    penalty = df["slow_mover"].astype(float) * w["slow_mover_penalty"]
    raw = (
        positive_stock * w["positive_stock"]
        + streak_component * w["zero_streak"]
        + demand_component * w["historical_demand"]
        + unchanged_component * w["inventory_unchanged"]
        + peer_component * w["peer_demand"]
        + promo_component * w["promotion"]
        - penalty
    )
    df["phantom_score"] = raw.clip(0, 100).round(2)
    df["candidate"] = (
        (df["on_hand"] > 0)
        & (df["zero_sales_streak"] >= config.ZERO_STREAK_MIN)
        & (df["expected_daily_sales"] >= config.MIN_EXPECTED_DAILY_SALES)
        & (~df["slow_mover"])
    )
    # Ambiguous pattern: zero sales but inventory is not frozen, or peer evidence is unavailable.
    ambiguous = df["candidate"] & (
        (df["inventory_days_unchanged"] < config.INVENTORY_UNCHANGED_DAYS)
        | (df["peer_store_sales"].isna())
    )
    df["alert_type"] = np.where(
        ~df["candidate"], "monitor",
        np.where(ambiguous, "possible_wrong_shelf", "likely_phantom_stockout")
    )
    df["recommended_action"] = np.where(
        ~df["candidate"], "Monitor for another day",
        np.where(ambiguous, "Check shelf location and planogram", "Check shelf and backroom")
    )
    df["confidence"] = np.select(
        [df["phantom_score"] >= 70, df["phantom_score"] >= 45],
        ["High", "Medium"], default="Low"
    )
    return df

def rank_alerts(scored, top_k=None):
    """Return at most top_k candidate alerts per store and date, ranked by score."""
    limit = top_k if top_k is not None else config.MAX_ALERTS_PER_STORE_DAY
    candidates = scored.loc[scored["candidate"]].copy()
    candidates = candidates.sort_values(["date", "store_id", "phantom_score", "sku_id"],
                                        ascending=[True, True, False, True])
    candidates["rank_in_store"] = candidates.groupby(["date", "store_id"]).cumcount() + 1
    candidates = candidates[candidates["rank_in_store"] <= limit]
    return candidates.reset_index(drop=True)
