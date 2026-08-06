"""
generate_dataset.py
--------------------
Builds the order-level fact table (100,000+ rows) by simulating orders
chronologically against each (Product, Warehouse) pair's inventory state.

Why simulate instead of pure random sampling per row?
Inventory Level, Demand, Stock Received, and Stock Issued must be internally
consistent (inventory can't go negative, stock is replenished only when it
runs low, etc.). Generating each order independently would break those
relationships instantly under any real scrutiny. Instead, this module walks
through orders in time order for every (product, warehouse) pair and
maintains running inventory state — the same pattern a real inventory
management system uses.
"""

import numpy as np
import pandas as pd

import config
from dimensions import build_all_dimensions


def _assign_orders_to_product_warehouse(rng, n_orders, products, warehouses, customers):
    """Randomly assign each order to a product, warehouse, and customer.
    Order volume is weighted by each product's demand rate so popular
    products realistically get more orders than niche ones."""
    weights = products["Daily Demand Rate"].values
    weights = weights / weights.sum()
    product_idx = rng.choice(len(products), size=n_orders, p=weights)
    warehouse_idx = rng.choice(len(warehouses), size=n_orders)
    customer_idx = rng.choice(len(customers), size=n_orders)

    orders = pd.DataFrame({
        "Product ID": products["Product ID"].values[product_idx],
        "Product Name": products["Product Name"].values[product_idx],
        "Category": products["Category"].values[product_idx],
        "Supplier": products["Supplier"].values[product_idx],
        "Warehouse": warehouses["Warehouse"].values[warehouse_idx],
        "Customer ID": customers["Customer ID"].values[customer_idx],
    })

    # Seasonal weighting: bias order dates toward Nov-Dec (retail peak season)
    day_offsets = rng.integers(0, config.TOTAL_DAYS + 1, size=n_orders)
    order_dates = config.START_DATE + day_offsets.astype("timedelta64[D]")
    month = pd.to_datetime(order_dates).month
    peak_boost = rng.random(n_orders) < np.where(np.isin(month, [11, 12]), 0.35, 0.08)
    # re-roll ~boosted fraction into Nov/Dec of a random year in range to create the seasonal spike
    n_boost = peak_boost.sum()
    if n_boost > 0:
        boosted_years = rng.choice([2024, 2025], size=n_boost)
        boosted_months = rng.choice([11, 12], size=n_boost)
        boosted_days = rng.integers(1, 28, size=n_boost)
        boosted_dates = pd.to_datetime({
            "year": boosted_years, "month": boosted_months, "day": boosted_days
        }).values.astype("datetime64[D]")
        order_dates = np.array(order_dates, dtype="datetime64[D]")
        order_dates[peak_boost] = boosted_dates

    orders["Order Date"] = pd.to_datetime(order_dates)
    orders["Order Quantity"] = rng.integers(1, 25, size=n_orders)
    return orders.sort_values(["Product ID", "Warehouse", "Order Date"]).reset_index(drop=True)


def _simulate_inventory(orders, products, warehouses, suppliers, rng):
    """Chronologically walk each (Product, Warehouse) group, maintaining a
    running inventory balance, and emit Inventory Level / Demand /
    Stock Received / Stock Issued for every order row."""

    prod_lookup = products.set_index("Product ID")
    wh_lookup = warehouses.set_index("Warehouse")
    sup_lookup = suppliers.set_index("Supplier")

    inv_level, demand_col, stock_received_col, stock_issued_col = (
        np.zeros(len(orders)), np.zeros(len(orders)),
        np.zeros(len(orders)), np.zeros(len(orders)),
    )

    # Group indices without re-sorting (orders is already sorted by Product, Warehouse, Date)
    for (product_id, warehouse), group in orders.groupby(["Product ID", "Warehouse"], sort=False):
        idx = group.index.values
        daily_rate = prod_lookup.loc[product_id, "Daily Demand Rate"]
        lead_time = int(sup_lookup.loc[prod_lookup.loc[product_id, "Supplier"], "Avg Lead Time Days"])

        # Safety stock & reorder point (standard formulas)
        demand_std = max(daily_rate * 0.3, 0.5)
        safety_stock = 1.65 * demand_std * np.sqrt(lead_time)          # ~95% service level
        reorder_point = daily_rate * lead_time + safety_stock
        eoq = max(daily_rate * 20, 20)                                   # target replenishment batch

        inventory = reorder_point + eoq * rng.uniform(0.5, 1.0)           # starting stock
        last_date = group["Order Date"].values[0]

        for i, row_idx in enumerate(idx):
            current_date = group["Order Date"].values[i]
            days_elapsed = max(int((current_date - last_date) / np.timedelta64(1, "D")), 0)

            # Background demand consumed inventory between the previous and this order
            interim_demand = rng.poisson(daily_rate * days_elapsed) if days_elapsed > 0 else 0
            inventory -= interim_demand

            received = 0.0
            if inventory < reorder_point:
                received = eoq * rng.uniform(0.9, 1.15)
                inventory += received

            qty = orders.at[row_idx, "Order Quantity"]
            issued = min(qty, max(inventory, 0))
            inventory -= issued

            demand_col[row_idx] = interim_demand + qty
            stock_received_col[row_idx] = round(received, 1)
            stock_issued_col[row_idx] = round(issued, 1)
            inv_level[row_idx] = round(max(inventory, 0), 1)

            last_date = current_date

    orders["Inventory Level"] = inv_level
    orders["Demand"] = demand_col.astype(int)
    orders["Stock Received"] = stock_received_col
    orders["Stock Issued"] = stock_issued_col
    return orders


CATEGORY_MODE_WEIGHTS = {
    # (Road, Rail, Air, Sea) — grocery never flies (perishable, low value);
    # electronics/mobiles justify air freight; furniture leans on rail/sea.
    "Grocery":                 [0.75, 0.20, 0.00, 0.05],
    "Beauty & Personal Care":   [0.62, 0.25, 0.08, 0.05],
    "Fashion":                  [0.50, 0.15, 0.25, 0.10],
    "Sports & Fitness":          [0.55, 0.15, 0.20, 0.10],
    "Appliances":                 [0.45, 0.20, 0.15, 0.20],
    "Home & Furniture":            [0.45, 0.15, 0.10, 0.30],
    "Electronics":                  [0.35, 0.15, 0.35, 0.15],
    "Mobiles & Accessories":         [0.35, 0.10, 0.45, 0.10],
}

# Probability an order ships within the same region (short haul) vs. cross-region.
# Grocery/beauty are distributed regionally; electronics/mobiles ship nationally
# from fewer central warehouses.
CATEGORY_SAME_REGION_PROB = {
    "Grocery": 0.80, "Beauty & Personal Care": 0.70, "Fashion": 0.55,
    "Sports & Fitness": 0.55, "Appliances": 0.50, "Home & Furniture": 0.50,
    "Electronics": 0.40, "Mobiles & Accessories": 0.40,
}


def _simulate_logistics(orders, warehouses, products, rng):
    """Assign transportation mode/carrier, compute distance, ship/delivery
    dates, cost, and derive Late Delivery Flag from mode reliability.
    Mode and distance are category-aware: a low-value grocery order has no
    business flying across the country, while electronics/mobiles justify
    air freight — matching how real logistics networks are actually run."""
    n = len(orders)
    wh_region = orders["Warehouse"].map(warehouses.set_index("Warehouse")["Region"])
    categories = orders["Category"].values

    modes = list(config.TRANSPORT_MODES.keys())
    mode_choice = np.empty(n, dtype=object)
    is_same_region = np.zeros(n, dtype=bool)
    for category, weights in CATEGORY_MODE_WEIGHTS.items():
        mask = categories == category
        n_cat = mask.sum()
        if n_cat == 0:
            continue
        mode_choice[mask] = rng.choice(modes, size=n_cat, p=weights)
        same_region_prob = CATEGORY_SAME_REGION_PROB[category]
        is_same_region[mask] = rng.random(n_cat) < same_region_prob

    carrier_choice = rng.choice(config.CARRIERS, size=n)

    # Distance: same-region deliveries are short; cross-region deliveries
    # are capped shorter for regionally-stocked categories (grocery/beauty
    # wouldn't realistically ship 3,000km cross-country) vs. nationally
    # distributed categories (electronics/mobiles/furniture).
    REGIONAL_CATEGORIES = {"Grocery", "Beauty & Personal Care"}
    cross_region_max = np.where(np.isin(categories, list(REGIONAL_CATEGORIES)), 1200, 3500)
    base_distance = np.where(
        is_same_region,
        rng.uniform(20, 300, n),
        rng.uniform(300, cross_region_max, size=n),
    )
    orders["Distance"] = np.round(base_distance, 1)

    speed = np.array([config.TRANSPORT_MODES[m]["speed_km_day"] for m in mode_choice])
    cost_per_kg_km = np.array([config.TRANSPORT_MODES[m]["cost_per_kg_km"] for m in mode_choice])
    base_reliability = np.array([config.TRANSPORT_MODES[m]["reliability"] for m in mode_choice])
    carrier_mod = np.array([config.CARRIER_RELIABILITY_MODIFIER[c] for c in carrier_choice])

    orders["Transportation Mode"] = mode_choice
    orders["Carrier"] = carrier_choice

    warehouse_processing = orders["Warehouse"].map(warehouses.set_index("Warehouse")["Avg Processing Days"])
    processing_days = np.maximum(rng.normal(warehouse_processing, 0.5), 0.1)
    orders["Ship Date"] = orders["Order Date"] + pd.to_timedelta(np.round(processing_days), unit="D")

    transit_days = orders["Distance"].values / speed + rng.normal(0, 0.4, n)
    transit_days = np.maximum(transit_days, 0.3)
    orders["Delivery Date"] = orders["Ship Date"] + pd.to_timedelta(np.round(transit_days), unit="D")

    # Promised delivery = SLA based on mode's "typical" transit + processing, with no delay noise
    promised_days = np.round(orders["Distance"].values / speed) + np.round(processing_days) + 1
    actual_days = (orders["Delivery Date"] - orders["Order Date"]).dt.days.values
    on_time_prob = np.clip(base_reliability * carrier_mod, 0.5, 0.99)
    is_late_roll = rng.random(n) > on_time_prob
    orders["Late Delivery Flag"] = np.where(
        (actual_days > promised_days) | is_late_roll, "Yes", "No"
    )

    # Shipping cost = weight × distance × mode rate + flat handling fee —
    # real freight pricing, not a distance-only formula. This is why a
    # single lightweight item no longer costs the same to ship as a
    # heavy bulk pallet of the same distance.
    unit_weight = orders["Product ID"].map(products.set_index("Product ID")["Unit Weight KG"]).values
    total_weight = unit_weight * orders["Order Quantity"].values
    orders["Shipping Cost"] = np.round(
        orders["Distance"].values * cost_per_kg_km * total_weight + config.SHIPMENT_HANDLING_FEE, 2
    )
    return orders


def _simulate_status_and_financials(orders, products, warehouses, suppliers, rng):
    n = len(orders)
    prod_lookup = products.set_index("Product ID")

    orders["Base Cost"] = orders["Product ID"].map(prod_lookup["Base Procurement Cost"])
    orders["Base Price"] = orders["Product ID"].map(prod_lookup["Base Selling Price"])
    orders["Procurement Cost"] = np.round(orders["Base Cost"] * orders["Order Quantity"] * rng.uniform(0.97, 1.03, n), 2)
    orders["Selling Price"] = np.round(orders["Base Price"] * orders["Order Quantity"] * rng.uniform(0.98, 1.05, n), 2)

    wh_storage = orders["Warehouse"].map(warehouses.set_index("Warehouse")["Storage Cost Per Unit"])
    orders["Warehouse Cost"] = np.round(wh_storage * orders["Order Quantity"] * rng.uniform(0.9, 1.2, n), 2)

    # Order status: mostly delivered, some cancelled/returned/backordered/in-transit
    statuses = list(config.ORDER_STATUS_WEIGHTS.keys())
    probs = list(config.ORDER_STATUS_WEIGHTS.values())
    orders["Order Status"] = rng.choice(statuses, size=n, p=probs)

    # Very recent orders (last 5 days of the window) can't be "Delivered" yet if lead/transit implies future date
    future_mask = orders["Delivery Date"] > pd.Timestamp(config.END_DATE)
    orders.loc[future_mask, "Order Status"] = "In Transit"

    orders["Delivery Status"] = np.select(
        [orders["Order Status"] == "Delivered", orders["Order Status"] == "In Transit",
         orders["Order Status"] == "Cancelled", orders["Order Status"] == "Backordered",
         orders["Order Status"] == "Returned"],
        ["Delivered", "In Transit", "Cancelled", "Pending", "Delivered"],
        default="Pending",
    )

    # Cancelled/Backordered orders have no meaningful delivery date
    no_delivery_mask = orders["Order Status"].isin(["Cancelled", "Backordered", "In Transit"])
    orders.loc[no_delivery_mask, "Delivery Date"] = pd.NaT
    orders.loc[no_delivery_mask, "Late Delivery Flag"] = "No"

    # Return Flag: driven by supplier defect rate + slightly higher for Apparel/Electronics
    defect_rate = orders["Supplier"].map(suppliers.set_index("Supplier")["Defect Rate"])
    category_bump = orders["Category"].isin(["Apparel", "Electronics"]).astype(float) * 0.02
    return_prob = np.clip(defect_rate.values + category_bump.values, 0, 0.25)
    organic_return = rng.random(n) < return_prob
    orders["Return Flag"] = np.where((orders["Order Status"] == "Returned") | organic_return, "Yes", "No")

    # Forecast Demand: actual demand distorted by category-specific noise (used in Step 6)
    noise_pct = orders["Product ID"].map(prod_lookup["Forecast Noise"])
    forecast_error = rng.normal(0, noise_pct, n)
    orders["Forecast Demand"] = np.maximum(np.round(orders["Demand"] * (1 + forecast_error)), 0).astype(int)

    return orders


def generate_dataset(n_orders: int = config.N_ORDERS, seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dims = build_all_dimensions(seed=seed)
    products, warehouses, suppliers, customers = (
        dims["products"], dims["warehouses"], dims["suppliers"], dims["customers"]
    )

    orders = _assign_orders_to_product_warehouse(rng, n_orders, products, warehouses, customers)
    orders = _simulate_inventory(orders, products, warehouses, suppliers, rng)
    orders = _simulate_logistics(orders, warehouses, products, rng)
    orders = _simulate_status_and_financials(orders, products, warehouses, suppliers, rng)

    orders["Order ID"] = [f"ORD{i:07d}" for i in range(1, len(orders) + 1)]
    orders["Region"] = orders["Warehouse"].map(warehouses.set_index("Warehouse")["Region"])

    final_cols = [
        "Order ID", "Customer ID", "Product ID", "Product Name", "Category", "Warehouse", "Region", "Supplier",
        "Order Date", "Ship Date", "Delivery Date",
        "Inventory Level", "Demand", "Stock Received", "Stock Issued",
        "Transportation Mode", "Carrier", "Distance",
        "Delivery Status", "Order Status", "Order Quantity",
        "Selling Price", "Procurement Cost", "Shipping Cost", "Warehouse Cost",
        "Return Flag", "Late Delivery Flag", "Forecast Demand",
    ]
    orders = orders[final_cols].sort_values("Order Date").reset_index(drop=True)
    return orders


if __name__ == "__main__":
    df = generate_dataset()
    print(f"Generated {len(df):,} rows, {df['Order ID'].nunique():,} unique orders")
    print(df.head(5).to_string(index=False))
    df.to_csv("../data/raw/supply_chain_orders.csv", index=False)
    print("\nSaved to data/raw/supply_chain_orders.csv")
