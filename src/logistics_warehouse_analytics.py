"""
logistics_warehouse_analytics.py
----------------------------------
Three related analyses that feed the Logistics and Warehouse Power BI pages:

1. Delivery performance  — on-time % by region, carrier, mode, warehouse;
   identifies where delays concentrate.
2. Logistics cost         — shipping cost breakdowns by carrier/mode/region,
   cost efficiency (cost per km, cost as % of revenue).
3. Warehouse performance  — order volume, processing speed, on-time %,
   perfect order rate, and inventory-based capacity utilization per warehouse.

Run: python3 logistics_warehouse_analytics.py
"""

import numpy as np
import pandas as pd

CLEAN_PATH = "../data/processed/supply_chain_orders_clean.csv"
WAREHOUSES_PATH = "../data/raw/dim_warehouses.csv"

OUT_DELIVERY = "../data/processed/delivery_performance.csv"
OUT_LOGISTICS_COST = "../data/processed/logistics_cost_summary.csv"
OUT_WAREHOUSE_PERF = "../data/processed/warehouse_performance.csv"


def load_data():
    orders = pd.read_csv(CLEAN_PATH, parse_dates=["Order Date", "Ship Date", "Delivery Date"])
    warehouses = pd.read_csv(WAREHOUSES_PATH)
    print(f"Loaded {len(orders):,} orders across {orders['Warehouse'].nunique()} warehouses")
    return orders, warehouses


def delivery_performance_analysis(orders: pd.DataFrame) -> dict:
    delivered = orders[orders["Is Delivered"]]

    overall_on_time = 1 - (delivered["Late Delivery Flag"] == "Yes").mean()
    print(f"\nOverall on-time delivery rate: {overall_on_time*100:.1f}%")

    def on_time_by(col):
        g = delivered.groupby(col).agg(
            Orders=("Order ID", "count"),
            Late_Deliveries=("Late Delivery Flag", lambda x: (x == "Yes").sum()),
            Avg_Delivery_Days=("Order To Delivery Days", "mean"),
            Avg_Delay_Days=("Delivery Delay Days", "mean"),
        )
        g["On Time %"] = round((1 - g["Late_Deliveries"] / g["Orders"]) * 100, 1)
        return g.sort_values("On Time %").round(2)

    by_region = on_time_by("Region")
    by_carrier = on_time_by("Carrier")
    by_mode = on_time_by("Transportation Mode")
    by_warehouse = on_time_by("Warehouse")

    print("\nMost delayed regions:\n", by_region.head(3)[["Orders", "On Time %"]])
    print("\nMost delayed carriers:\n", by_carrier.head(3)[["Orders", "On Time %"]])

    combined = pd.concat(
        {"Region": by_region, "Carrier": by_carrier, "Mode": by_mode, "Warehouse": by_warehouse},
        names=["Dimension", "Value"],
    ).reset_index()
    combined.to_csv(OUT_DELIVERY, index=False)
    print(f"\nSaved delivery performance breakdown to {OUT_DELIVERY}")
    return {"region": by_region, "carrier": by_carrier, "mode": by_mode, "warehouse": by_warehouse}


def logistics_cost_analysis(orders: pd.DataFrame) -> pd.DataFrame:
    valid = orders[orders["Order Status"] != "Cancelled"]

    def cost_by(col):
        g = valid.groupby(col).agg(
            Orders=("Order ID", "count"),
            Total_Shipping_Cost=("Shipping Cost", "sum"),
            Avg_Shipping_Cost=("Shipping Cost", "mean"),
            Total_Revenue=("Selling Price", "sum"),
            Avg_Distance=("Distance", "mean"),
        )
        g["Shipping Cost as % of Revenue"] = round(g["Total_Shipping_Cost"] / g["Total_Revenue"] * 100, 2)
        g["Cost Per KM"] = round(g["Total_Shipping_Cost"] / (g["Avg_Distance"] * g["Orders"]), 2)
        return g.round(1).sort_values("Total_Shipping_Cost", ascending=False)

    by_carrier = cost_by("Carrier")
    by_mode = cost_by("Transportation Mode")
    by_region = cost_by("Region")

    print("\n--- Logistics cost by carrier ---")
    print(by_carrier[["Orders", "Total_Shipping_Cost", "Shipping Cost as % of Revenue"]])
    print("\n--- Logistics cost by transportation mode ---")
    print(by_mode[["Orders", "Total_Shipping_Cost", "Shipping Cost as % of Revenue"]])

    combined = pd.concat(
        {"Carrier": by_carrier, "Mode": by_mode, "Region": by_region},
        names=["Dimension", "Value"],
    ).reset_index()
    combined.to_csv(OUT_LOGISTICS_COST, index=False)
    print(f"\nSaved logistics cost summary to {OUT_LOGISTICS_COST}")
    return combined


def warehouse_performance_analysis(orders: pd.DataFrame, warehouses: pd.DataFrame) -> pd.DataFrame:
    valid = orders[orders["Order Status"] != "Cancelled"]

    perf = valid.groupby("Warehouse").agg(
        Total_Orders=("Order ID", "count"),
        Total_Revenue=("Selling Price", "sum"),
        Total_Warehouse_Cost=("Warehouse Cost", "sum"),
        Avg_Processing_Days=("Order To Ship Days", "mean"),
        Late_Deliveries=("Late Delivery Flag", lambda x: (x == "Yes").sum()),
        Delivered_Orders=("Is Delivered", "sum"),
        Returns=("Return Flag", lambda x: (x == "Yes").sum()),
    ).reset_index()

    perf["On Time %"] = round((1 - perf["Late_Deliveries"] / perf["Delivered_Orders"]) * 100, 1)
    perf["Return Rate %"] = round(perf["Returns"] / perf["Total_Orders"] * 100, 1)
    # Perfect order = delivered, on time, not returned
    perfect = valid[
        (valid["Is Delivered"]) & (valid["Late Delivery Flag"] == "No") & (valid["Return Flag"] == "No")
    ].groupby("Warehouse")["Order ID"].count().rename("Perfect_Orders")
    perf = perf.merge(perfect, on="Warehouse", how="left").fillna({"Perfect_Orders": 0})
    perf["Perfect Order Rate %"] = round(perf["Perfect_Orders"] / perf["Total_Orders"] * 100, 1)

    # Inventory-based capacity utilization: latest known inventory level for
    # every (Product, Warehouse) pair, summed per warehouse, vs. its capacity.
    latest_inv = (
        orders.sort_values("Order Date")
        .groupby(["Warehouse", "Product ID"])["Inventory Level"]
        .last()
        .reset_index()
        .groupby("Warehouse")["Inventory Level"]
        .sum()
        .rename("Current Inventory Units")
    )
    perf = perf.merge(latest_inv, on="Warehouse", how="left")
    perf = perf.merge(warehouses[["Warehouse", "Region", "Hub City", "Capacity Units"]], on="Warehouse")
    perf["Utilization %"] = round(perf["Current Inventory Units"] / perf["Capacity Units"] * 100, 1)

    perf = perf.sort_values("Total_Revenue", ascending=False)
    cols = ["Warehouse", "Region", "Hub City", "Total_Orders", "Total_Revenue", "Avg_Processing_Days",
            "On Time %", "Perfect Order Rate %", "Return Rate %", "Utilization %", "Capacity Units"]
    print("\n--- Warehouse performance ---")
    print(perf[cols].to_string(index=False))

    perf.to_csv(OUT_WAREHOUSE_PERF, index=False)
    print(f"\nSaved warehouse performance summary to {OUT_WAREHOUSE_PERF}")
    return perf


def main():
    orders, warehouses = load_data()
    delivery_performance_analysis(orders)
    logistics_cost_analysis(orders)
    warehouse_performance_analysis(orders, warehouses)


if __name__ == "__main__":
    main()
