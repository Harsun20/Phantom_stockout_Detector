"""Transparent heuristic risk scoring and daily alert ranking."""
import numpy as np
import pandas as pd
from . import config

def score_features(features):
    """Add candidate flag, 0-100 score, confidence, alert type, and action."""
    frame = features.copy()
    w = config.WEIGHTS
    positive = frame["on_hand"].gt(0).astype(float) * w["positive_stock"]
    streak = (frame["zero_sales_streak"] / max(config.MIN_ZERO_STREAK * 2, 1)).clip(0, 1) * w["zero_streak"]
    demand = (frame["expected_daily_sales"] / 2.0).clip(0, 1) * w["expected_demand"]
    unchanged = (frame["inventory_days_unchanged"] / 7.0).clip(0, 1) * w["inventory_unchanged"]
    peer = np.where(frame["peer_store_sales"].fillna(0) > 0, w["peer_demand"], 0)
    promo = frame["promo_active"].fillna(False).astype(bool).astype(float) * w["promotion"]
    penalty = frame["slow_mover"].fillna(True).astype(bool).astype(float) * w["slow_mover_penalty"]
    raw = positive + streak + demand + unchanged + peer + promo - penalty
    frame["phantom_score"] = np.round(np.clip(raw, 0, 100), 1)
    frame["candidate"] = (
        frame["on_hand"].gt(0)
        & frame["zero_sales_streak"].ge(config.MIN_ZERO_STREAK)
        & frame["expected_daily_sales"].ge(config.MIN_EXPECTED_DEMAND)
        & ~frame["slow_mover"]
    )
    frame.loc[~frame["candidate"], "phantom_score"] = frame.loc[~frame["candidate"], "phantom_score"].clip(upper=44.9)
    frame["confidence"] = np.select(
        [frame["phantom_score"] >= config.HIGH_CONFIDENCE_SCORE,
         frame["phantom_score"] >= config.MEDIUM_CONFIDENCE_SCORE],
        ["High", "Medium"], default="Low"
    )
    frame["alert_type"] = np.select(
        [frame["candidate"] & frame["peer_store_sales"].fillna(0).gt(0),
         frame["candidate"] & frame["inventory_days_unchanged"].ge(5)],
        ["likely_phantom_stockout", "possible_wrong_shelf"],
        default="monitor"
    )
    frame["recommended_action"] = np.select(
        [frame["alert_type"].eq("possible_wrong_shelf"),
         frame["alert_type"].eq("likely_phantom_stockout")],
        ["Check shelf location and planogram", "Check shelf and backroom"],
        default="Monitor for another day"
    )
    return frame

def rank_alerts(scored, top_k=None):
    """Return top-k candidate alerts per date/store, ranked by score."""
    top_k = config.DEFAULT_TOP_K if top_k is None else max(0, int(top_k))
    candidates = scored[scored["candidate"]].copy()
    candidates = candidates.sort_values(
        ["date", "store_id", "phantom_score", "expected_daily_sales"],
        ascending=[True, True, False, False]
    )
    candidates["rank_in_store"] = candidates.groupby(["date", "store_id"]).cumcount() + 1
    candidates = candidates[candidates["rank_in_store"] <= top_k]
    return candidates.reset_index(drop=True)
