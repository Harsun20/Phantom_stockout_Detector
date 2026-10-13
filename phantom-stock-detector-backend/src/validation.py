"""Data quality checks and a readable validation summary."""
import pandas as pd

KEYS = ["date", "store_id", "sku_id"]

def validate_data(data, verbose=True):
    """Validate required tables; safely drop malformed rows and reject duplicate keys."""
    sales = data["sales"].copy()
    inventory = data["inventory"].copy()
    issues = []
    for name, frame, value_col in [
        ("sales", sales, "units_sold"), ("inventory", inventory, "on_hand")
    ]:
        before = len(frame)
        frame = frame.dropna(subset=KEYS + [value_col])
        frame = frame[frame[value_col] >= 0]
        dropped = before - len(frame)
        if dropped:
            issues.append(f"{name}: excluded {dropped} invalid row(s) (missing key/value or negative value)")
        duplicates = int(frame.duplicated(KEYS, keep=False).sum())
        if duplicates:
            raise ValueError(f"{name} contains {duplicates} rows with duplicate date-store-sku keys. Resolve duplicates first.")
        data[name] = frame
    sales_keys = set(map(tuple, data["sales"][KEYS].astype(str).to_numpy()))
    inventory_keys = set(map(tuple, data["inventory"][KEYS].astype(str).to_numpy()))
    overlap = len(sales_keys & inventory_keys)
    union = len(sales_keys | inventory_keys)
    if overlap == 0:
        raise ValueError("Sales and inventory have no overlapping date-store-sku keys.")
    if verbose:
        for name in ("sales", "inventory"):
            frame = data[name]
            dates = frame["date"].dropna()
            date_range = f"{dates.min().date()} to {dates.max().date()}" if not dates.empty else "no valid dates"
            print(f"{name}: {len(frame)} valid rows; {date_range}")
        print(f"Join coverage: {overlap}/{union} distinct sales/inventory keys overlap ({overlap / union:.1%}).")
        for issue in issues:
            print(f"Validation note: {issue}")
    data["validation_summary"] = {
        "sales_rows": len(data["sales"]), "inventory_rows": len(data["inventory"]),
        "overlapping_keys": overlap, "union_keys": union, "notes": issues
    }
    return data
