"""Create time-series features without using future or same-day sales."""
import numpy as np
import pandas as pd
from . import config

KEYS = ["date", "store_id", "sku_id"]

def build_features(tables):
    """Merge inputs and calculate historical demand, streak, peer and inventory features."""
    sales = tables["sales"].copy()
    inventory = tables["inventory"].copy()
    df = sales.merge(inventory, on=KEYS, how="inner", validate="one_to_one")
    if df.empty:
        raise ValueError("Sales and inventory did not produce any merged rows.")
    promos = tables.get("promotions")
    if promos is not None and not promos.empty:
        df = df.merge(promos[KEYS + ["promo_active"]].drop_duplicates(KEYS), on=KEYS, how="left", validate="many_to_one")
    else:
        df["promo_active"] = False
    df["promo_active"] = df["promo_active"].fillna(False).astype(bool)

    stores = tables.get("stores")
    if stores is not None and not stores.empty:
        metadata = stores.drop_duplicates("store_id")
        df = df.merge(metadata, on="store_id", how="left", validate="many_to_one")
    else:
        for col in ("store_format", "store_size", "city_tier"):
            df[col] = np.nan

    products = tables.get("products")
    if products is not None and not products.empty:
        df = df.merge(products.drop_duplicates("sku_id"), on="sku_id", how="left", validate="many_to_one")
    else:
        df["sku_name"] = np.nan
        df["category"] = np.nan
        df["selling_price"] = np.nan

    df = df.sort_values(["store_id", "sku_id", "date"]).reset_index(drop=True)
    group = df.groupby(["store_id", "sku_id"], sort=False, group_keys=False)
    df["is_zero_sale"] = (df["units_sold"] == 0).astype(int)
    def streak(series):
        values = []
        count = 0
        for value in series:
            count = count + 1 if value == 1 else 0
            values.append(count)
        return pd.Series(values, index=series.index)
    df["zero_sales_streak"] = group["is_zero_sale"].transform(streak)

    # shift(1) ensures today's sales are never part of today's expected-demand baseline.
    prior_sales = group["units_sold"].shift(1)
    df["_prior_sales"] = prior_sales
    df["expected_daily_sales"] = df.groupby(["store_id", "sku_id"], sort=False)["_prior_sales"].transform(
        lambda s: s.rolling(config.ROLLING_WINDOW_DAYS, min_periods=config.ROLLING_MIN_PERIODS).mean()
    )
    # Early rows lack 7 prior observations. Use an expanding prior-only mean as a useful fallback.
    fallback = df.groupby(["store_id", "sku_id"], sort=False)["_prior_sales"].transform(lambda s: s.expanding(min_periods=1).mean())
    df["expected_daily_sales"] = df["expected_daily_sales"].fillna(fallback).fillna(0).clip(lower=0)
    df = df.drop(columns=["_prior_sales"])

    df["slow_mover"] = df["expected_daily_sales"] < config.SLOW_MOVER_THRESHOLD
    changed = group["on_hand"].transform(lambda s: s.ne(s.shift(1)))
    # Each new inventory value starts a new run; cumulative run length gives consecutive unchanged days.
    df["_inventory_run"] = changed.groupby([df["store_id"], df["sku_id"]]).cumsum()
    df["inventory_days_unchanged"] = df.groupby(["store_id", "sku_id", "_inventory_run"], sort=False).cumcount() + 1
    df = df.drop(columns=["_inventory_run"])

    # Peer benchmark is leave-one-out, matching store format and city tier.
    if stores is not None and not stores.empty and {"store_format", "city_tier"}.issubset(df.columns):
        peer_group_cols = ["date", "sku_id", "store_format", "city_tier"]
        totals = df.groupby(peer_group_cols, dropna=False)["units_sold"].transform("sum")
        counts = df.groupby(peer_group_cols, dropna=False)["units_sold"].transform("count")
        df["peer_store_sales"] = ((totals - df["units_sold"]) / (counts - 1)).where(counts > 1, np.nan)
    else:
        df["peer_store_sales"] = np.nan
    df["expected_lost_units"] = df["expected_daily_sales"] * df["zero_sales_streak"]
    return df
