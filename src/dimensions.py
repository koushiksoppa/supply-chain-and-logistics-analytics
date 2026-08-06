"""
dimensions.py
-------------
Builds the "master data" tables that the order-level fact table references:
products, warehouses, suppliers, and customers.

In a real company these would live in separate systems (PIM, WMS, SRM, CRM).
Modeling them as distinct tables here — instead of inlining random values into
every order row — is what makes the joins in Step 7 (SQL) and the data model
in Step 8 (Power BI) look like a real star schema instead of a flat CSV.
"""

import numpy as np
import pandas as pd
from faker import Faker

import config

# Indian locale gives realistic company names (suppliers) and person/city
# names, matching the Flipkart-style reskin of this dataset.
fake = Faker("en_IN")

# Category-specific descriptor words used to build product names like
# "boAt Airdopes 141 True Wireless Earbuds" or "Amul Gold Full Cream Milk".
CATEGORY_DESCRIPTORS = {
    "Mobiles & Accessories": ["5G Smartphone", "True Wireless Earbuds", "Fast Charger", "Smartwatch", "Bluetooth Neckband"],
    "Electronics":            ["4K Smart TV", "Soundbar", "Laptop", "Home Theatre System", "Bluetooth Speaker"],
    "Fashion":                 ["Slim Fit Shirt", "Running Shoes", "Denim Jacket", "Cotton Kurta", "Casual Sneakers"],
    "Home & Furniture":         ["3-Seater Sofa", "Study Table", "Wardrobe", "Bookshelf", "Bed with Storage"],
    "Appliances":                ["Front Load Washing Machine", "Double Door Refrigerator", "Microwave Oven", "Air Conditioner", "Mixer Grinder"],
    "Grocery":                    ["Gold Full Cream Milk", "Basmati Rice 5kg", "Refined Sunflower Oil", "Whole Wheat Atta", "Masala Tea"],
    "Beauty & Personal Care":      ["Face Wash", "Herbal Shampoo", "Vitamin C Serum", "Body Lotion", "Sunscreen SPF 50"],
    "Sports & Fitness":              ["Yoga Mat", "Cricket Kit", "Badminton Racquet", "Resistance Band Set", "Football"],
}


def build_products(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    categories = list(config.CATEGORIES.keys())
    for i in range(1, config.N_PRODUCTS + 1):
        category = rng.choice(categories)
        cfg = config.CATEGORIES[category]
        cost = round(rng.uniform(*cfg["cost_range"]), 2)
        margin = rng.uniform(*cfg["margin_range"])
        price = round(cost * (1 + margin), 2)
        daily_demand_rate = rng.uniform(*cfg["demand_rate"])

        brand = rng.choice(config.CATEGORY_BRANDS[category])
        descriptor = rng.choice(CATEGORY_DESCRIPTORS[category])
        model_code = f"{rng.integers(10, 999)}"
        product_name = f"{brand} {descriptor} {model_code}"

        rows.append({
            "Product ID": f"P{i:05d}",
            "Product Name": product_name,
            "Category": category,
            "Brand": brand,
            "Base Procurement Cost": cost,
            "Base Selling Price": price,
            "Daily Demand Rate": round(daily_demand_rate, 2),
            "Forecast Noise": cfg["forecast_noise"],
            "Unit Weight KG": round(rng.uniform(0.1, 25.0), 2),
        })
    return pd.DataFrame(rows)


def build_warehouses(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(1, config.N_WAREHOUSES + 1):
        region = config.REGIONS[(i - 1) % len(config.REGIONS)]
        rows.append({
            "Warehouse": f"WH{i:02d}",
            "Region": region,
            "Hub City": config.REGION_HUB_CITY[region],
            "Capacity Units": int(rng.integers(20_000, 80_000)),
            # processing efficiency: avg days to pick/pack before shipping
            "Avg Processing Days": round(rng.uniform(0.5, 2.5), 2),
            "Storage Cost Per Unit": round(rng.uniform(2.5, 12.0), 2),  # INR per unit
        })
    return pd.DataFrame(rows)


def build_suppliers(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(1, config.N_SUPPLIERS + 1):
        rows.append({
            "Supplier": f"SUP{i:03d}",
            "Supplier Name": fake.company(),
            "Avg Lead Time Days": int(rng.integers(3, 21)),
            # defect rate drives a portion of the Return Flag logic
            "Defect Rate": round(rng.uniform(0.005, 0.06), 4),
            "Reliability Score": round(rng.uniform(0.80, 0.99), 3),
        })
    return pd.DataFrame(rows)


def build_customers(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(1, config.N_CUSTOMERS + 1):
        region = rng.choice(config.REGIONS)
        rows.append({
            "Customer ID": f"CUST{i:06d}",
            "Customer Region": region,
            "Customer City": config.REGION_HUB_CITY[region],
        })
    return pd.DataFrame(rows)


def build_all_dimensions(seed: int = config.RANDOM_SEED):
    rng = np.random.default_rng(seed)
    Faker.seed(seed)
    products = build_products(rng)
    warehouses = build_warehouses(rng)
    suppliers = build_suppliers(rng)
    customers = build_customers(rng)

    # Assign each product a primary supplier (many-to-one, realistic)
    products["Supplier"] = rng.choice(suppliers["Supplier"], size=len(products))

    return {
        "products": products,
        "warehouses": warehouses,
        "suppliers": suppliers,
        "customers": customers,
    }


if __name__ == "__main__":
    dims = build_all_dimensions()
    for name, df in dims.items():
        print(f"\n{name.upper()}  ({len(df)} rows)")
        print(df.head(3).to_string(index=False))
