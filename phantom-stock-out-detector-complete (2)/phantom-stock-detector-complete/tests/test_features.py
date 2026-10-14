import pandas as pd
from src.feature_engineering import build_features

def small_tables(sales_values):
    dates = pd.date_range("2026-01-01", periods=len(sales_values))
    sales = pd.DataFrame({"date":dates,"store_id":"S1","sku_id":"K1","units_sold":sales_values})
    inventory = pd.DataFrame({"date":dates,"store_id":"S1","sku_id":"K1","on_hand":20})
    return {"sales":sales,"inventory":inventory,"promotions":None,"stores":None,"products":None}

def test_zero_streak_resets_after_positive_sale():
    features = build_features(small_tables([1,0,0,2,0,0]))
    assert features["zero_sales_streak"].tolist() == [0,1,2,0,1,2]

def test_expected_demand_uses_prior_sales_not_same_day():
    # The second row's expected demand is the first row's sale, not its own large sale.
    features = build_features(small_tables([2,100] + [1]*8))
    assert features.loc[1, "expected_daily_sales"] == 2
