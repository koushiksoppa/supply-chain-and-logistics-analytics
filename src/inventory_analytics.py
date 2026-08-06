"""
inventory_analytics.py
------------------------
Product-level inventory analytics: ABC classification (Pareto revenue
analysis), Economic Order Quantity (EOQ), statistically-derived Safety
Stock, and Reorder Point (ROP).

All formulas are the standard textbook/industry ones — the point of this
module isn't novelty, it's applying them correctly to real transactional
data and being able to explain every assumption.

Run: python3 inventory_analytics.py
"""

import numpy as np
import pandas as pd

CLEAN_PATH = "../data/processed/supply_chain_orders_clean.csv"
PRODUCTS_PATH = "../data/raw/dim_products.csv"
SUPPLIERS_PATH = "../data/raw/dim_suppliers.csv"
OUT_PATH = "../data/processed/inventory_analytics.csv"

# --------------------------------------------------------------------
# Business assumptions (stated explicitly — any real inventory model
# requires these inputs from Finance/Ops; they're not derivable from
# transactional data alone)
# --------------------------------------------------------------------
ORDERING_COST_PER_PO = 500.0        # ₹ cost to place one purchase order (staff time, processing)
HOLDING_COST_RATE = 0.20            # 20% of unit procurement cost held in inventory per year
SERVICE_LEVEL_Z = 1.65              # Z-score for a 95% service level (safety stock)
DATASET_YEARS = 2.0                 # the raw dataset spans 2024-01-01 to 2025-12-31

# ABC thresholds on cumulative revenue share (classic 70/20/10 Pareto split,
# tuned slightly for a long-tail catalog like an e-commerce marketplace)
ABC_THRESHOLDS = {"A": 0.70, "B": 0.90}  # C = everything beyond 0.90


def load_data():
    orders = pd.read_csv(CLEAN_PATH, parse_dates=["Order Date"])
    products = pd.read_csv(PRODUCTS_PATH)
    suppliers = pd.read_csv(SUPPLIERS_PATH)
    print(f"Loaded {len(orders):,} orders, {len(products)} products, {len(suppliers)} suppliers")
    return orders, products, suppliers


def compute_abc_classification(orders: pd.DataFrame) -> pd.DataFrame:
    """Classify products by their share of total revenue (excluding
    cancelled orders, which never generated real revenue)."""
    valid = orders[orders["Order Status"] != "Cancelled"]
    revenue_by_product = (
        valid.groupby(["Product ID", "Product Name", "Category"])["Selling Price"]
        .sum()
        .reset_index()
        .rename(columns={"Selling Price": "Total Revenue"})
        .sort_values("Total Revenue", ascending=False)
        .reset_index(drop=True)
    )
    revenue_by_product["Revenue Share"] = revenue_by_product["Total Revenue"] / revenue_by_product["Total Revenue"].sum()
    revenue_by_product["Cumulative Revenue Share"] = revenue_by_product["Revenue Share"].cumsum()

    def classify(cum_share):
        if cum_share <= ABC_THRESHOLDS["A"]:
            return "A"
        elif cum_share <= ABC_THRESHOLDS["B"]:
            return "B"
        return "C"

    revenue_by_product["ABC Class"] = revenue_by_product["Cumulative Revenue Share"].apply(classify)
    return revenue_by_product


def compute_demand_stats(orders: pd.DataFrame) -> pd.DataFrame:
    """Observed daily demand mean/std per product, computed from actual
    transactional data (not the hidden simulation parameters) — this is
    what a real analyst would calculate from historical order history."""
    daily = (
        orders.groupby(["Product ID", "Order Date"])["Demand"]
        .sum()
        .reset_index()
    )
    # Reindex to include zero-demand days so std isn't biased upward by only
    # counting days that had at least one order.
    full_range = pd.date_range(orders["Order Date"].min(), orders["Order Date"].max(), freq="D")
    stats_rows = []
    for pid, grp in daily.groupby("Product ID"):
        series = grp.set_index("Order Date")["Demand"].reindex(full_range, fill_value=0)
        stats_rows.append({
            "Product ID": pid,
            "Avg Daily Demand": round(series.mean(), 3),
            "Demand Std Dev": round(series.std(), 3),
            "Total Observed Demand": int(series.sum()),
        })
    return pd.DataFrame(stats_rows)


def compute_eoq_safety_stock_rop(demand_stats, products, suppliers) -> pd.DataFrame:
    df = demand_stats.merge(products[["Product ID", "Base Procurement Cost", "Supplier"]], on="Product ID")
    df = df.merge(suppliers[["Supplier", "Avg Lead Time Days"]], on="Supplier", how="left")

    # Annual demand (D): observed total demand over the dataset's time span, annualized
    df["Annual Demand"] = round(df["Total Observed Demand"] / DATASET_YEARS, 1)

    # Holding cost per unit per year (H)
    df["Holding Cost Per Unit"] = round(df["Base Procurement Cost"] * HOLDING_COST_RATE, 2)

    # EOQ = sqrt(2 * D * S / H)
    df["EOQ"] = np.round(
        np.sqrt((2 * df["Annual Demand"] * ORDERING_COST_PER_PO) / df["Holding Cost Per Unit"]), 0
    )

    # Safety Stock = Z * demand_std_dev * sqrt(lead_time_days)
    df["Safety Stock"] = np.round(
        SERVICE_LEVEL_Z * df["Demand Std Dev"] * np.sqrt(df["Avg Lead Time Days"]), 1
    )

    # Reorder Point = (avg_daily_demand * lead_time) + safety_stock
    df["Reorder Point"] = np.round(
        df["Avg Daily Demand"] * df["Avg Lead Time Days"] + df["Safety Stock"], 1
    )

    # Number of purchase orders per year implied by this EOQ (for cost validation)
    df["Orders Per Year"] = np.round(df["Annual Demand"] / df["EOQ"].replace(0, np.nan), 1)
    df["Annual Ordering Cost"] = round(df["Orders Per Year"] * ORDERING_COST_PER_PO, 0)
    df["Annual Holding Cost"] = round((df["EOQ"] / 2) * df["Holding Cost Per Unit"], 0)
    df["Annual Inventory Cost"] = df["Annual Ordering Cost"] + df["Annual Holding Cost"]

    return df


def flag_reorder_needed(orders: pd.DataFrame, inventory_df: pd.DataFrame) -> pd.DataFrame:
    """Compare each product's most recent known Inventory Level against its
    Reorder Point — this is the actionable output a planner would act on."""
    latest_inventory = (
        orders.sort_values("Order Date")
        .groupby("Product ID")["Inventory Level"]
        .last()
        .reset_index()
        .rename(columns={"Inventory Level": "Latest Inventory Level"})
    )
    inventory_df = inventory_df.merge(latest_inventory, on="Product ID", how="left")
    inventory_df["Reorder Needed"] = inventory_df["Latest Inventory Level"] < inventory_df["Reorder Point"]
    return inventory_df


def main():
    orders, products, suppliers = load_data()

    print("\n--- ABC Classification ---")
    abc = compute_abc_classification(orders)
    class_summary = abc.groupby("ABC Class").agg(
        Product_Count=("Product ID", "count"),
        Revenue_Share=("Revenue Share", "sum"),
    ).round(3)
    print(class_summary)

    print("\n--- Demand statistics (observed from order history) ---")
    demand_stats = compute_demand_stats(orders)
    print(demand_stats.describe().round(2))

    print("\n--- EOQ / Safety Stock / Reorder Point ---")
    inventory = compute_eoq_safety_stock_rop(demand_stats, products, suppliers)
    inventory = flag_reorder_needed(orders, inventory)
    print(inventory[["Product ID", "Annual Demand", "EOQ", "Safety Stock", "Reorder Point",
                      "Latest Inventory Level", "Reorder Needed"]].head(8).to_string(index=False))

    final = abc.merge(inventory, on="Product ID", how="left")
    final = final.sort_values("Total Revenue", ascending=False)

    final.to_csv(OUT_PATH, index=False)
    print(f"\nSaved to {OUT_PATH}")
    print(f"Final shape: {final.shape[0]} products, {final.shape[1]} columns")

    print(f"\nProducts needing reorder right now: {final['Reorder Needed'].sum()} "
          f"({final['Reorder Needed'].mean()*100:.1f}% of catalog)")


if __name__ == "__main__":
    main()
