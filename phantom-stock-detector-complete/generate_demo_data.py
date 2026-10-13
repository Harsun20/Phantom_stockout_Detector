"""Generate deterministic synthetic retail data for local demonstrations."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

def generate():
    """Create sales, inventory, optional metadata and synthetic ground truth CSVs."""
    DATA.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261013)
    dates = pd.date_range("2026-01-01", periods=90, freq="D")
    stores = pd.DataFrame([
        {"store_id":"S001","store_format":"Urban","store_size":1800,"city_tier":"Tier1"},
        {"store_id":"S002","store_format":"Urban","store_size":1650,"city_tier":"Tier1"},
        {"store_id":"S003","store_format":"Neighborhood","store_size":900,"city_tier":"Tier2"},
    ])
    products = []
    for i in range(1, 31):
        products.append({
            "sku_id":f"SKU{i:03d}", "sku_name":f"Demo Product {i:02d}",
            "category":["Grocery","Personal Care","Home","Beverage"][i % 4],
            "selling_price":round(float(rng.uniform(35, 650)), 2),
            "base_demand":0.08 if i in (4, 9, 14, 19, 24, 29) else float(rng.uniform(0.8, 4.0))
        })
    prod = pd.DataFrame(products)
    phantom_cases = {("S001","SKU002"): 58, ("S002","SKU006"): 64, ("S003","SKU011"): 53}
    real_stockout = ("S001", "SKU015", 70)
    ambiguous_case = ("S002", "SKU018", 60)
    sales_rows, inventory_rows, promo_rows, truth_rows = [], [], [], []
    for store in stores.to_dict("records"):
        for product in prod.to_dict("records"):
            sku = product["sku_id"]
            initial_stock = int(rng.integers(18, 65))
            current_stock = initial_stock
            for day_idx, date in enumerate(dates):
                weekday_factor = 1.25 if date.dayofweek in (4, 5) else (0.78 if date.dayofweek == 0 else 1.0)
                promo = bool((day_idx in (20, 21, 45, 46, 72) and int(sku[-3:]) % 5 == 0))
                demand = product["base_demand"] * weekday_factor * (1.55 if promo else 1.0)
                sold = int(rng.poisson(demand))
                case_key = (store["store_id"], sku)
                phantom_start = phantom_cases.get(case_key)
                is_phantom = phantom_start is not None and day_idx >= phantom_start
                if is_phantom:
                    sold = 0
                    # Inventory remains frozen at a positive recorded count.
                elif case_key == (real_stockout[0], real_stockout[1]) and day_idx >= real_stockout[2]:
                    current_stock = 0
                    sold = 0
                elif case_key == (ambiguous_case[0], ambiguous_case[1]) and day_idx >= ambiguous_case[2]:
                    sold = 0 if day_idx % 2 == 0 else int(rng.integers(0, 2))
                    # Small inconsistent inventory changes create an ambiguous pattern.
                    current_stock = max(2, current_stock - int(sold))
                else:
                    sold = min(sold, current_stock)
                    current_stock = max(0, current_stock - sold)
                    if current_stock < 8 and rng.random() < 0.18:
                        current_stock += int(rng.integers(10, 30))
                # For phantom cases, freeze inventory from the first suspicious day onward.
                if is_phantom and day_idx == phantom_start:
                    current_stock = max(current_stock, int(rng.integers(8, 20)))
                sales_rows.append({"date":date.date().isoformat(),"store_id":store["store_id"],"sku_id":sku,"units_sold":sold})
                inventory_rows.append({"date":date.date().isoformat(),"store_id":store["store_id"],"sku_id":sku,"on_hand":current_stock})
                promo_rows.append({"date":date.date().isoformat(),"store_id":store["store_id"],"sku_id":sku,"promo_active":promo})
                truth_rows.append({"date":date.date().isoformat(),"store_id":store["store_id"],"sku_id":sku,"is_phantom":bool(is_phantom)})
    pd.DataFrame(sales_rows).to_csv(DATA/"demo_sales.csv", index=False)
    pd.DataFrame(inventory_rows).to_csv(DATA/"demo_inventory.csv", index=False)
    pd.DataFrame(promo_rows).to_csv(DATA/"demo_promotions.csv", index=False)
    stores.to_csv(DATA/"demo_stores.csv", index=False)
    prod.drop(columns=["base_demand"]).to_csv(DATA/"demo_products.csv", index=False)
    pd.DataFrame(truth_rows).to_csv(DATA/"demo_ground_truth.csv", index=False)
    print("Created six synthetic CSV files in data/.")
    print("Demo only: synthetic ground truth is for evaluation and is not used by scoring.")

if __name__ == "__main__":
    generate()
