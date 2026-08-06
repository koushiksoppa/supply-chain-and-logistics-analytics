"""
load_to_sql.py
----------------
Loads the cleaned fact table and dimension tables into a SQLite database
using the star schema defined in sql/01_schema.sql.

SQLite is used here so the whole project runs with zero external database
setup -- but the schema (proper PK/FK, indexes, star design) is written to
translate directly to Postgres/MySQL/SQL Server if this were a real
production pipeline.

Run: python3 load_to_sql.py
"""

import sqlite3
import pandas as pd

DB_PATH = "../sql/supply_chain.db"
SCHEMA_PATH = "../sql/01_schema.sql"

CLEAN_ORDERS_PATH = "../data/processed/supply_chain_orders_clean.csv"
PRODUCTS_PATH = "../data/raw/dim_products.csv"
WAREHOUSES_PATH = "../data/raw/dim_warehouses.csv"
SUPPLIERS_PATH = "../data/raw/dim_suppliers.csv"
CUSTOMERS_PATH = "../data/raw/dim_customers.csv"

# Maps: DataFrame column -> sql column name, kept explicit (no magic
# lowercasing) so it's obvious exactly what's going into the database.
ORDER_COLUMN_MAP = {
    "Order ID": "order_id", "Customer ID": "customer_id", "Product ID": "product_id",
    "Category": "category", "Warehouse": "warehouse_id", "Region": "region",
    "Supplier": "supplier_id", "Order Date": "order_date", "Ship Date": "ship_date",
    "Delivery Date": "delivery_date", "Inventory Level": "inventory_level", "Demand": "demand",
    "Stock Received": "stock_received", "Stock Issued": "stock_issued",
    "Transportation Mode": "transportation_mode", "Carrier": "carrier", "Distance": "distance_km",
    "Delivery Status": "delivery_status", "Order Status": "order_status",
    "Order Quantity": "order_quantity", "Selling Price": "selling_price",
    "Procurement Cost": "procurement_cost", "Shipping Cost": "shipping_cost",
    "Warehouse Cost": "warehouse_cost", "Total Cost": "total_cost", "Profit": "profit",
    "Profit Margin %": "profit_margin_pct", "Return Flag": "return_flag",
    "Late Delivery Flag": "late_delivery_flag", "Forecast Demand": "forecast_demand",
    "Forecast Error %": "forecast_error_pct", "Is Delivered": "is_delivered",
    "Order To Ship Days": "order_to_ship_days", "Order To Delivery Days": "order_to_delivery_days",
    "Delivery Delay Days": "delivery_delay_days", "Fill Rate": "fill_rate",
    "Stockout Flag": "stockout_flag", "Order Year": "order_year", "Order Month": "order_month",
    "Order Quarter": "order_quarter",
}

PRODUCT_COLUMN_MAP = {
    "Product ID": "product_id", "Product Name": "product_name", "Category": "category",
    "Brand": "brand", "Base Procurement Cost": "base_procurement_cost",
    "Base Selling Price": "base_selling_price", "Daily Demand Rate": "daily_demand_rate",
    "Unit Weight KG": "unit_weight_kg", "Supplier": "supplier_id",
}

WAREHOUSE_COLUMN_MAP = {
    "Warehouse": "warehouse_id", "Region": "region", "Hub City": "hub_city",
    "Capacity Units": "capacity_units", "Avg Processing Days": "avg_processing_days",
    "Storage Cost Per Unit": "storage_cost_per_unit",
}

SUPPLIER_COLUMN_MAP = {
    "Supplier": "supplier_id", "Supplier Name": "supplier_name",
    "Avg Lead Time Days": "avg_lead_time_days", "Defect Rate": "defect_rate",
    "Reliability Score": "reliability_score",
}

CUSTOMER_COLUMN_MAP = {
    "Customer ID": "customer_id", "Customer Region": "customer_region",
    "Customer City": "customer_city",
}


def build_database():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    print("Schema created (fact_orders + 4 dimension tables + indexes)")

    # Dimensions first (fact table has FK references to these)
    suppliers = pd.read_csv(SUPPLIERS_PATH).rename(columns=SUPPLIER_COLUMN_MAP)[list(SUPPLIER_COLUMN_MAP.values())]
    suppliers.to_sql("dim_suppliers", conn, if_exists="append", index=False)

    warehouses = pd.read_csv(WAREHOUSES_PATH).rename(columns=WAREHOUSE_COLUMN_MAP)[list(WAREHOUSE_COLUMN_MAP.values())]
    warehouses.to_sql("dim_warehouses", conn, if_exists="append", index=False)

    customers = pd.read_csv(CUSTOMERS_PATH).rename(columns=CUSTOMER_COLUMN_MAP)[list(CUSTOMER_COLUMN_MAP.values())]
    customers.to_sql("dim_customers", conn, if_exists="append", index=False)

    products = pd.read_csv(PRODUCTS_PATH).rename(columns=PRODUCT_COLUMN_MAP)[list(PRODUCT_COLUMN_MAP.values())]
    products.to_sql("dim_products", conn, if_exists="append", index=False)

    print(f"Loaded dimensions: {len(suppliers)} suppliers, {len(warehouses)} warehouses, "
          f"{len(customers)} customers, {len(products)} products")

    orders = pd.read_csv(CLEAN_ORDERS_PATH)
    orders = orders.rename(columns=ORDER_COLUMN_MAP)[list(ORDER_COLUMN_MAP.values())]
    # SQLite booleans as 0/1
    orders["is_delivered"] = orders["is_delivered"].astype(int)
    orders["stockout_flag"] = orders["stockout_flag"].astype(int)
    orders.to_sql("fact_orders", conn, if_exists="append", index=False)
    print(f"Loaded {len(orders):,} rows into fact_orders")

    conn.commit()
    conn.close()
    print(f"\nDatabase built at {DB_PATH}")


def sanity_check():
    conn = sqlite3.connect(DB_PATH)
    for table in ["fact_orders", "dim_products", "dim_warehouses", "dim_suppliers", "dim_customers"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count:,} rows")

    # Referential integrity spot check: every product_id in fact_orders should exist in dim_products
    orphans = conn.execute("""
        SELECT COUNT(*) FROM fact_orders f
        LEFT JOIN dim_products p ON f.product_id = p.product_id
        WHERE p.product_id IS NULL
    """).fetchone()[0]
    print(f"Orphaned product_id references in fact_orders: {orphans}")
    conn.close()


if __name__ == "__main__":
    build_database()
    print("\n--- Sanity check ---")
    sanity_check()
