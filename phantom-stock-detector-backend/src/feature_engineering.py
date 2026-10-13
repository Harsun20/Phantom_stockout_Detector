"""Build leakage-safe daily features from sales and inventory."""
import numpy as np
import pandas as pd
from .config import ROLLING_WINDOW_DAYS, ROLLING_MIN_PERIODS, SLOW_MOVER_THRESHOLD

KEYS = ["date", "store_id", "sku_id"]

def build_features(data):
    """Merge input tables and calculate historical demand, streaks, and peer context."""
    sales = data["sales"].copy()
    inventory = data["inventory"].copy()
    merged = pd.merge(sales, inventory, on=KEYS, how="inner", validate="one_to_one")
    if merged.empty:
        raise ValueError("No overlapping sales and inventory rows remain after merging.")
    merged = merged.sort_values(["store_id", "sku_id", "date"]).reset_index(drop=True)
    for column, default in [("units_sold", 0), ("on_hand", 0)]:
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(default).clip(lower=0)
    if data.get("promotions") is not None:
        promos = data["promotions"].drop_duplicates(KEYS, keep="last")
        merged = merged.merge(promos, on=KEYS, how="left", validate="one_to_one")
    if "promo_active" not in merged:
        merged["promo_active"] = False
    merged["promo_active"] = merged["promo_active"].fillna(False).astype(bool)

    if data.get("stores") is not None:
        merged = merged.merge(data["stores"].drop_duplicates("store_id"), on="store_id", how="left")
    else:
        for col in ["store_format", "store_size", "city_tier"]:
            merged[col] = np.nan
    if data.get("products") is not None:
        merged = merged.merge(data["products"].drop_duplicates("sku_id"), on="sku_id", how="left")

    grouped = merged.groupby(["store_id", "sku_id"], sort=False, group_keys=False)
    merged["is_zero_sale"] = merged["units_sold"].eq(0)
    merged["zero_sales_streak"] = grouped["is_zero_sale"].transform(
        lambda series: series.groupby((~series).cumsum()).cumsum().astype(int)
    )
    # Shift first so today's sales never contribute to today's expected demand.
    merged["expected_daily_sales"] = grouped["units_sold"].transform(
        lambda series: series.shift(1).rolling(ROLLING_WINDOW_DAYS, min_periods=ROLLING_MIN_PERIODS).mean()
    ).fillna(0.0)
    merged["slow_mover"] = merged["expected_daily_sales"] < SLOW_MOVER_THRESHOLD

    def unchanged_streak(series):
        changed = series.ne(series.shift(1))
        groups = changed.cumsum()
        return series.groupby(groups).cumcount() + 1
    merged["inventory_days_unchanged"] = merged.groupby(["store_id", "sku_id"], sort=False)["on_hand"].transform(unchanged_streak).astype(int)

    # Peer benchmark uses other stores only, matching format and city tier when possible.
    merged["peer_store_sales"] = np.nan
    metadata_available = data.get("stores") is not None
    if metadata_available:
        for _, indices in merged.groupby(["sku_id", "date"], dropna=False).groups.items():
            rows = merged.loc[indices]
            for idx, row in rows.iterrows():
                peers = rows[rows["store_id"] != row["store_id"]]
                if pd.notna(row.get("store_format")):
                    peers = peers[peers["store_format"] == row["store_format"]]
                if pd.notna(row.get("city_tier")):
                    peers = peers[peers["city_tier"] == row["city_tier"]]
                if not peers.empty:
                    merged.at[idx, "peer_store_sales"] = float(peers["units_sold"].mean())
    merged["expected_lost_units"] = merged["expected_daily_sales"] * merged["zero_sales_streak"]
    return merged
