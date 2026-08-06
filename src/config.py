"""
config.py
---------
Central configuration for the synthetic supply chain dataset generator.
Keeping these as named constants (not magic numbers scattered in code)
makes the generator auditable and easy to re-tune later.
"""

import numpy as np

# --------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------
RANDOM_SEED = 42

# --------------------------------------------------------------------
# Scale
# --------------------------------------------------------------------
N_ORDERS = 100_000
N_PRODUCTS = 400
N_WAREHOUSES = 8
N_SUPPLIERS = 25
N_CUSTOMERS = 20_000

# --------------------------------------------------------------------
# Time window: 2 full years of order history
# --------------------------------------------------------------------
START_DATE = np.datetime64("2024-01-01")
END_DATE = np.datetime64("2025-12-31")
TOTAL_DAYS = int((END_DATE - START_DATE) / np.timedelta64(1, "D"))

# --------------------------------------------------------------------
# Product categories, matching Flipkart's real top-level category taxonomy.
# Cost/price ranges are in INR (₹) at realistic Indian retail price points.
# (selling_price = procurement_cost * (1 + margin))
# --------------------------------------------------------------------
CURRENCY = "INR"
CURRENCY_SYMBOL = "₹"

CATEGORIES = {
    "Mobiles & Accessories": {"cost_range": (1500, 70000),  "margin_range": (0.08, 0.18), "demand_rate": (2, 12), "forecast_noise": 0.35},
    "Electronics":            {"cost_range": (2000, 90000),  "margin_range": (0.10, 0.22), "demand_rate": (1, 8),  "forecast_noise": 0.33},
    "Fashion":                 {"cost_range": (250, 4500),    "margin_range": (0.35, 0.65), "demand_rate": (2, 15), "forecast_noise": 0.30},
    "Home & Furniture":         {"cost_range": (600, 45000),   "margin_range": (0.22, 0.42), "demand_rate": (1, 6),  "forecast_noise": 0.26},
    "Appliances":                {"cost_range": (1800, 55000),  "margin_range": (0.15, 0.28), "demand_rate": (1, 5),  "forecast_noise": 0.24},
    "Grocery":                    {"cost_range": (30, 900),       "margin_range": (0.12, 0.25), "demand_rate": (5, 25), "forecast_noise": 0.12},
    "Beauty & Personal Care":      {"cost_range": (100, 2500),      "margin_range": (0.30, 0.55), "demand_rate": (3, 18), "forecast_noise": 0.20},
    "Sports & Fitness":              {"cost_range": (300, 8000),       "margin_range": (0.25, 0.48), "demand_rate": (1, 9),  "forecast_noise": 0.23},
}

# Realistic brand pools per category, used to generate product names like
# "boAt Airdopes 141 True Wireless Earbuds" instead of a bare SKU code.
CATEGORY_BRANDS = {
    "Mobiles & Accessories": ["Samsung", "Redmi", "realme", "vivo", "OPPO", "boAt", "Noise", "OnePlus", "Motorola", "iQOO"],
    "Electronics":            ["Samsung", "LG", "Sony", "boAt", "JBL", "Mi", "HP", "Dell", "Lenovo", "Acer"],
    "Fashion":                 ["Roadster", "HRX", "Allen Solly", "Levis", "Puma", "Adidas", "Van Heusen", "Biba", "W", "U.S. Polo Assn."],
    "Home & Furniture":         ["Nilkamal", "Godrej Interio", "Urban Ladder", "@home", "Solimo", "Pepperfry", "Durian", "Wakefit"],
    "Appliances":                ["LG", "Samsung", "Whirlpool", "Voltas", "Haier", "Bosch", "IFB", "Prestige", "Bajaj"],
    "Grocery":                    ["Amul", "Tata", "Fortune", "Aashirvaad", "Haldiram's", "Nestle", "Britannia", "Patanjali"],
    "Beauty & Personal Care":      ["Lakme", "Mamaearth", "Nivea", "L'Oreal", "The Man Company", "WOW", "Himalaya", "Plum"],
    "Sports & Fitness":              ["Nivia", "Cosco", "Yonex", "Decathlon", "Boldfit", "Nike", "Reebok", "Kore"],
}

# --------------------------------------------------------------------
# Regions: modeled on Flipkart's real fulfillment-center zones across India
# --------------------------------------------------------------------
REGIONS = ["North", "South", "East", "West", "Central"]

REGION_HUB_CITY = {
    "North": "Delhi NCR",
    "South": "Bengaluru",
    "East": "Kolkata",
    "West": "Mumbai",
    "Central": "Nagpur",
}

# --------------------------------------------------------------------
# Realistic per-category unit weight ranges (kg) — needed so shipping cost
# (which scales with weight × distance, like real freight pricing) doesn't
# charge a lightweight item the same as a heavy one.
# --------------------------------------------------------------------
CATEGORY_UNIT_WEIGHT_KG = {
    "Mobiles & Accessories": (0.05, 1.0),
    "Electronics":            (0.5, 15.0),
    "Fashion":                 (0.1, 1.5),
    "Home & Furniture":         (5.0, 80.0),
    "Appliances":                (4.0, 60.0),
    "Grocery":                    (0.2, 5.0),
    "Beauty & Personal Care":      (0.05, 2.0),
    "Sports & Fitness":              (0.2, 10.0),
}

# --------------------------------------------------------------------
# Transportation modes: avg speed (km/day), cost per KG per KM (₹) — real
# freight pricing scales with weight carried, not distance alone — and
# base on-time reliability
# --------------------------------------------------------------------
TRANSPORT_MODES = {
    "Road": {"speed_km_day": 450,  "cost_per_kg_km": 0.028, "reliability": 0.90},
    "Rail": {"speed_km_day": 600,  "cost_per_kg_km": 0.015, "reliability": 0.85},
    "Air":  {"speed_km_day": 3000, "cost_per_kg_km": 0.090, "reliability": 0.96},
    "Sea":  {"speed_km_day": 350,  "cost_per_kg_km": 0.010, "reliability": 0.80},
}

# Flat handling/booking fee (₹) applied per shipment regardless of weight —
# mirrors real carrier minimum charges.
SHIPMENT_HANDLING_FEE = 35.0

# Real logistics providers that actually move Flipkart's parcels in India
CARRIERS = [
    "Ekart Logistics", "Delhivery", "Blue Dart", "DTDC", "XpressBees", "Ecom Express",
]

# Each carrier's reliability modifier applied on top of the mode's base reliability
CARRIER_RELIABILITY_MODIFIER = {
    "Ekart Logistics": 1.05,
    "Delhivery": 1.02,
    "Blue Dart": 1.08,
    "DTDC": 0.93,
    "XpressBees": 0.95,
    "Ecom Express": 0.90,
}

ORDER_STATUS_WEIGHTS = {
    "Delivered": 0.85,
    "Returned": 0.05,
    "Cancelled": 0.05,
    "Backordered": 0.03,
    "In Transit": 0.02,
}
