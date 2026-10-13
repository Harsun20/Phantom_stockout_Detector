"""Generate deterministic synthetic CSVs, including labelled demo anomalies."""
from pathlib import Path
import numpy as np
import pandas as pd

def generate(output_dir="data", seed=42):
    """Write all six demo CSV files and return their paths."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-01", periods=90, freq="D")
    stores = pd.DataFrame({
        "store_id": ["S001", "S002", "S003"],
        "store_format": ["urban", "urban", "suburban"],
        "store_size": [1200, 1100, 900],
        "city_tier": ["Tier1", "Tier1", "Tier2"],
    })
    products = []
    for i in range(1, 31):
        products.append({
            "sku_id": f"SKU{i:03d}", "sku_name": f"Demo Product {i:02d}",
            "category": ["Grocery", "Personal Care", "Household"][i % 3],
            "selling_price": round(float(rng.uniform(40, 650)), 2),
        })
    products = pd.DataFrame(products)
    sales_rows, inventory_rows, promo_rows, truth_rows = [], [], [], []
    phantom_cases = {("S001", "SKU003", 55), ("S002", "SKU008", 62), ("S003", "SKU011", 48)}
    wrong_shelf = ("S001", "SKU015", 66)
    real_stockout = ("S002", "SKU020", 40)
    for store in stores["store_id"]:
        for i in range(1, 31):
            sku = f"SKU{i:03d}"
            base = 0.08 if i in (1, 2, 4, 7, 13) else float(rng.uniform(0.8, 3.8))
            inventory = int(rng.integers(8, 45))
            anomaly_start = None
            anomaly_type = None
            for day_index, date in enumerate(dates):
                weekday_factor = 1.25 if date.dayofweek in (4, 5) else (0.72 if date.dayofweek == 0 else 1.0)
                promo = bool(day_index in (20, 21, 22, 70, 71) and i in (3, 8, 15, 21))
                demand = base * weekday_factor * (1.7 if promo else 1.0)
                sold = int(rng.poisson(demand))
                if (store, sku, day_index) in phantom_cases:
                    anomaly_start, anomaly_type = day_index, "phantom"
                if (store, sku, day_index) == wrong_shelf:
                    anomaly_start, anomaly_type = day_index, "wrong_shelf"
                if (store, sku, day_index) == real_stockout:
                    anomaly_start, anomaly_type = day_index, "real_stockout"
                if anomaly_start is not None and day_index >= anomaly_start:
                    if anomaly_type in ("phantom", "wrong_shelf"):
                        sold = 0
                        # Leave system inventory frozen at a positive count.
                    elif anomaly_type == "real_stockout":
                        inventory = 0
                        sold = 0
                else:
                    # Inventory is replenished sometimes and reduced by sales.
                    inventory = max(0, inventory - sold)
                    if inventory < 5 and rng.random() < 0.35:
                        inventory += int(rng.integers(12, 30))
                sales_rows.append({"date": date.date().isoformat(), "store_id": store, "sku_id": sku, "units_sold": sold})
                inventory_rows.append({"date": date.date().isoformat(), "store_id": store, "sku_id": sku, "on_hand": inventory})
                promo_rows.append({"date": date.date().isoformat(), "store_id": store, "sku_id": sku, "promo_active": promo})
                if anomaly_type in ("phantom", "wrong_shelf") and anomaly_start == day_index:
                    truth_rows.append({"date": date.date().isoformat(), "store_id": store, "sku_id": sku, "is_phantom": True})
    pd.DataFrame(sales_rows).to_csv(out / "demo_sales.csv", index=False)
    pd.DataFrame(inventory_rows).to_csv(out / "demo_inventory.csv", index=False)
    pd.DataFrame(promo_rows).to_csv(out / "demo_promotions.csv", index=False)
    stores.to_csv(out / "demo_stores.csv", index=False)
    products.to_csv(out / "demo_products.csv", index=False)
    pd.DataFrame(truth_rows).to_csv(out / "demo_ground_truth.csv", index=False)
    return [out / name for name in ["demo_sales.csv", "demo_inventory.csv", "demo_promotions.csv", "demo_stores.csv", "demo_products.csv", "demo_ground_truth.csv"]]

if __name__ == "__main__":
    paths = generate()
    print("Generated synthetic demo files:")
    for path in paths:
        print(f" - {path}")
