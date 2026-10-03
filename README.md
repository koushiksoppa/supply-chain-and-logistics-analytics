# 📦 Supply Chain Analytics Dashboard

An end-to-end supply chain analytics project modeled on a Flipkart-style Indian e-commerce operation — built to demonstrate industry-level analytics work, not a tutorial walkthrough. Covers Python data engineering, SQL business intelligence, and a fully-specified Power BI executive dashboard.

## Business Problem

A growing e-commerce operation needs visibility into where its supply chain is losing money and service quality: which warehouses are over/under capacity, which categories are hardest to forecast, where delivery delays concentrate, and which products are chronically at risk of stockout. This project builds that visibility from raw transactional data up through a 6-page executive dashboard, and closes with 34 concrete, numbers-backed recommendations.

## Solution

A five-layer pipeline: a chronologically-simulated (not randomly sampled) 100,000-order dataset → Python cleaning and feature engineering → four dedicated analytics modules (inventory, logistics/warehouse, demand forecasting) → a star-schema SQL database with a 15-query business library → a fully documented Power BI dashboard spec (DAX measures + page-by-page build guide). Every number in the insights report traces back to a reproducible script.

## Tech Stack

Python (pandas, numpy, statsmodels, matplotlib, Faker) · SQL (SQLite, star schema) · Power BI (DAX, data model) · Git/GitHub

## Dataset

100,000 synthetic but internally-consistent orders (2024–2025) across 400 products, 8 warehouses (mapped to real Flipkart fulfillment-center cities: Delhi NCR, Bengaluru, Kolkata, Mumbai, Nagpur), 25 suppliers, and 20,000 customers. Generated via a chronological inventory simulation — orders are processed in date order against a running per-product-warehouse inventory balance with real reorder-point logic — rather than random sampling per row, so inventory levels, delivery delays, and costs are internally consistent. Currency is ₹ (INR); categories, brands, and logistics partners (Ekart, Delhivery, Blue Dart, DTDC, XpressBees, Ecom Express) match Flipkart's real business. Full methodology in `src/generate_dataset.py`.

## Architecture

```
generate_dataset.py (chronological order + inventory simulation)
              │
              ▼
clean_and_engineer.py (missing values, outlier flags, 19 engineered features)
              │
      ┌───────┼────────────────┬──────────────────────┐
      ▼       ▼                ▼                       ▼
inventory_  logistics_warehouse_  demand_forecasting.py
analytics.py  analytics.py
      │       │                │
      └───────┴────────────────┴───► data/processed/*.csv
                                              │
                          ┌───────────────────┼───────────────────┐
                          ▼                                       ▼
              load_to_sql.py → sql/supply_chain.db      powerbi/data/ → Power BI
              (star schema, 15-query library)            (DAX measures, 6-page dashboard)
```

## Key Findings

See the full **[Business Insights & Recommendations report](reports/business_insights_and_recommendations.md)** for all 34 findings. Highlights:

- **Overall on-time delivery: 92.3%**, but Central region trails at 88.0% — traced to one warehouse (WH05, Nagpur) with 3.7x slower processing time than the network's fastest facility.
- **Every product in the 400-SKU catalog is below its calculated reorder point.** Confirmed three independent ways (Python EOQ model, raw stockout flags, SQL queries) — the current safety-stock policy structurally underestimates real demand volatility (avg. coefficient of variation ≈ 2.9).
- **ABC classification is a clean, unforced Pareto curve**: 20% of products drive 69.9% of revenue.
- **Warehouse capacity is badly imbalanced**: WH08 (Kolkata) runs at 135.3% utilization while two Delhi NCR warehouses sit near 56%.
- **A trend-only forecast failed at ~100% MAPE on the Nov/Dec holiday window**; an explicit seasonal-index model cut that to 17.9% MAPE — seasonality is the single largest source of forecast error in this business.
- **Air freight costs 2.5x more (as % of revenue) than Sea/Rail**, concentrated in 4 identifiable high-cost North-region routes — a quantified, low-risk cost-reduction target.

## KPIs Implemented

Total Orders · Revenue (₹1,705.6 Cr) · Profit (₹283.0 Cr) · Profit Margin % · On-Time Delivery % · Fill Rate · Stockout Rate · Return Rate · Perfect Order Rate · Warehouse Utilization % · Logistics Cost as % of Revenue · Forecast Accuracy % · ABC Classification · EOQ / Safety Stock / Reorder Point · Backorders · Inventory Turnover

## Repository Structure

```
Supply-Chain-Analytics/
│
├── data/
│   ├── raw/                        → generated orders + dimension tables
│   └── processed/                   → cleaned dataset + all analytics outputs
├── sql/
│   ├── 01_schema.sql                 → star schema: fact_orders + 4 dimensions, indexes
│   ├── 02_views.sql                   → reusable views
│   ├── 03_business_queries.sql         → 15 validated business-question queries
│   └── supply_chain.db                  → built SQLite database (gitignored — rebuild via src/load_to_sql.py)
├── powerbi/
│   ├── data/                            → 6 CSVs ready for Power BI import (incl. dim_date)
│   ├── DAX_measures.md                   → ~35 KPI measures
│   └── DASHBOARD_BUILD_GUIDE.md            → page-by-page build guide, 6 dashboard pages
├── images/
│   ├── charts/                            → matplotlib EDA/forecast charts
│   └── dashboard_screenshots/              → Power BI page exports (add after building locally)
├── src/
│   ├── config.py                            → categories, regions, transport modes, business assumptions
│   ├── dimensions.py                         → builds product/warehouse/supplier/customer master data
│   ├── generate_dataset.py                    → chronological order + inventory simulation
│   ├── clean_and_engineer.py                   → missing values, outlier flagging, feature engineering
│   ├── inventory_analytics.py                   → ABC classification, EOQ, safety stock, reorder point
│   ├── logistics_warehouse_analytics.py          → delivery performance, logistics cost, warehouse KPIs
│   ├── demand_forecasting.py                      → monthly/regional trends, forecast accuracy, time series
│   └── load_to_sql.py                              → builds the SQLite database from processed CSVs
├── reports/
│   ├── business_insights_and_recommendations.md    → 34 insights, 6 categories, top-5 priorities
│   ├── resume_bullets.md                             → 5 ATS-friendly resume bullets
│   └── linkedin_post.md                               → LinkedIn announcement post
├── docs/
│   └── interview_prep.md                               → 110 Q&A: SQL, Power BI, Python, Supply Chain Analytics
├── notebooks/, dashboard/
├── README.md
├── requirements.txt
└── LICENSE
```

## Installation

```bash
git clone <your-repo-url>
cd Supply-Chain-Analytics
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Regenerate the full pipeline from scratch:

```bash
cd src
python3 generate_dataset.py
python3 clean_and_engineer.py
python3 inventory_analytics.py
python3 logistics_warehouse_analytics.py
python3 demand_forecasting.py
python3 load_to_sql.py
```

For Power BI, open Power BI Desktop and follow `powerbi/DASHBOARD_BUILD_GUIDE.md` starting at Section 1.

## Dashboard Preview

*Screenshots go here once the dashboard is built locally (Power BI Desktop isn't available in the environment this project was developed in — see `powerbi/DASHBOARD_BUILD_GUIDE.md` for the full spec to build all 6 pages). Add exported page images to `images/dashboard_screenshots/` and reference them here.*

## Results

- Consolidated 100,000 transactional records into a governed star-schema data model spanning inventory, logistics, and financial performance
- Identified and quantified 5 top-priority operational issues (see the insights report's priority ranking), each traceable to specific, reproducible metrics rather than generic recommendations
- Built a demand forecasting approach that improved holdout accuracy from ~0% (naive trend model) to 82.1% (seasonal-index model) on the hardest test window (holiday peak season)
- Delivered a fully specified 6-page Power BI dashboard covering all 18 required KPIs and 18 visualization types

## Future Improvements

- Incorporate real weather/holiday-calendar features into the forecasting model
- Move from a flat safety-stock assumption to a per-SKU one based on observed demand variance (see insight #8)
- Add supplier-level defect/on-time scorecards feeding directly into procurement decisions
- Extend the SQL layer to a hosted Postgres instance for a live, queryable public demo
- A/B test the Air-to-Road freight substitution recommended in insight #21 and measure realized savings

## License

MIT — see [LICENSE](LICENSE).
