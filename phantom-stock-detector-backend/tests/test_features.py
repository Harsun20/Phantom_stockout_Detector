import pandas as pd
from src.feature_engineering import build_features

def sample_data(sales_values):
    dates = pd.date_range("2026-01-01", periods=len(sales_values))
    keys = {"date": dates, "store_id": ["S1"] * len(dates), "sku_id": ["X1"] * len(dates)}
    return {
        "sales": pd.DataFrame({**keys, "units_sold": sales_values}),
        "inventory": pd.DataFrame({**keys, "on_hand": [10] * len(dates)}),
        "promotions": None, "stores": None, "products": None
    }

def test_zero_streak_resets_after_positive_sale():
    features = build_features(sample_data([0, 0, 2, 0, 0]))
    assert features["zero_sales_streak"].tolist() == [1, 2, 0, 1, 2]

def test_expected_demand_does_not_use_same_day_sales():
    values = [1] * 7 + [100]
    features = build_features(sample_data(values))
    assert features.iloc[7]["expected_daily_sales"] == 1
