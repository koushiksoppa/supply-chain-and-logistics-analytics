# 📦 Supply Chain Analytics Dashboard


An end-to-end supply chain analytics project modeled on a Flipkart-style Indian e-commerce operation: data engineering (Python), business intelligence querying (SQL — upcoming), and executive-level dashboarding (Power BI — upcoming). Built to demonstrate practical, industry-style analytics work, not a tutorial walkthrough.

## Business Problem

A growing e-commerce operation needs visibility into where its supply chain is losing money and service quality: which warehouses are over/under capacity, which categories are hardest to forecast, where delivery delays concentrate, and which products are chronically at risk of stockout. This project builds that visibility from raw transactional data up to (eventually) an executive Power BI dashboard.

## Tech Stack

Python (pandas, numpy, statsmodels, matplotlib) · SQL (upcoming) · Power BI (upcoming) · Git/GitHub

## Dataset

100,000 synthetic but internally-consistent orders (2024–2025) across 400 products, 8 warehouses (mapped to real Flipkart fulfillment-center cities: Delhi NCR, Bengaluru, Kolkata, Mumbai, Nagpur), 25 suppliers, and 20,000 customers. Generated via a chronological inventory simulation (not random sampling per row) so that inventory levels, delivery delays, and costs are internally consistent — see `src/generate_dataset.py` for the full methodology. Currency is ₹ (INR); categories, brands, and logistics partners (Ekart, Delhivery, Blue Dart, DTDC, XpressBees, Ecom Express) match Flipkart's real business.

## Architecture

```
Raw generation (src/generate_dataset.py)
        ↓
Cleaning + feature engineering (src/clean_and_engineer.py)
        ↓
   ┌────┴─────┬──────────────────────┬─────────────────────┐
Inventory   Logistics/Warehouse    Demand Forecasting
analytics   analytics              & time series
        ↓
data/processed/*.csv  →  (upcoming) SQL layer  →  (upcoming) Power BI
```

## Key Findings So Far

- **Overall on-time delivery: 92.3%** across ~89,600 delivered/returned orders, but with a real gap — the Central region trails at 88.0% on-time vs. 91–92% elsewhere.
- **Average fill rate is 56.9%**, driven by a genuine stockout pattern: 43.5% of order events occur when on-hand inventory is at or below zero. Cross-checked two independent ways (raw stockout flag, and a from-scratch EOQ/reorder-point model) — both agree the current safety-stock policy underestimates real demand variability (avg. demand coefficient of variation ≈ 2.9).
- **ABC classification is a clean Pareto curve**: 79 products (20% of catalog) drive 69.9% of revenue; 230 products (57% of catalog) drive only 10.1%. This emerged from the simulation rather than being forced.
- **Every product in the catalog is currently below its calculated reorder point** — a strong signal for the recommendations section: the fixed reorder logic doesn't account for per-SKU demand volatility.
- **Forecast accuracy varies sharply by category**: Grocery forecasts well (90.6% accuracy) while Mobiles & Accessories and Electronics are hardest to predict (72.0% and 73.7%) — consistent with how volatile fast-moving tech demand really is versus staple goods.
- **Warehouse capacity is badly imbalanced**: WH08 (Kolkata) runs at 135.3% utilization while WH01/WH06 (Delhi NCR) sit near 56–57% — a concrete rebalancing opportunity.
- **Air freight costs ~2.0% of revenue vs. ~0.7% for Sea/Rail** — quantifies the real cost of speed, and the data shows grocery/beauty categories correctly never use air freight (regionally distributed, low unit value).
- **Average profit margin is 17.6%**, ranging from 6.3% (Grocery, thin-margin staples) to 30.9% (Fashion, high-margin categories) — matches real retail intuition.

## KPIs Implemented

Total Orders · Revenue (₹1,705.6 Cr) · Profit (₹283.0 Cr) · Profit Margin % · On-Time Delivery % · Fill Rate · Stockout Rate · Return Rate · Perfect Order Rate · Warehouse Utilization % · Logistics Cost as % of Revenue · Forecast Accuracy % · ABC Classification · EOQ / Safety Stock / Reorder Point

## Repository Structure

```
Supply-Chain-Analytics/
│
├── data/
│   ├── raw/                    → generated orders + dimension tables (products, warehouses, suppliers, customers)
│   └── processed/               → cleaned/feature-engineered dataset + all analytics outputs
├── notebooks/                    → (upcoming) exploratory notebooks
├── sql/                            → (upcoming) schema, queries, views
├── powerbi/                          → (upcoming) .pbix file
├── images/
│   ├── charts/                        → matplotlib EDA/forecast charts generated in Steps 4–6
│   └── dashboard_screenshots/          → (upcoming) Power BI page exports
├── src/
│   ├── config.py                        → categories, regions, transport modes, business assumptions
│   ├── dimensions.py                     → builds product/warehouse/supplier/customer master data
│   ├── generate_dataset.py                → chronological order + inventory simulation
│   ├── clean_and_engineer.py               → missing values, outlier flagging, feature engineering
│   ├── inventory_analytics.py               → ABC classification, EOQ, safety stock, reorder point
│   ├── logistics_warehouse_analytics.py      → delivery performance, logistics cost, warehouse KPIs
│   └── demand_forecasting.py                  → monthly/regional trends, forecast accuracy, time series
├── reports/                     → (upcoming) written insights + recommendations
├── dashboard/                    → (upcoming) dashboard export assets
├── docs/
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

To regenerate the full analytics pipeline from scratch:

```bash
cd src
python3 generate_dataset.py
python3 clean_and_engineer.py
python3 inventory_analytics.py
python3 logistics_warehouse_analytics.py
python3 demand_forecasting.py
```

## Roadmap

- [x] Step 1: Project structure & environment setup
- [x] Step 2: Synthetic dataset generation (100,000 orders, chronological inventory simulation, Flipkart-style reskin)
- [x] Step 3: Data cleaning, missing-value handling, outlier flagging, feature engineering
- [x] Step 4: Inventory analytics — ABC classification, EOQ, safety stock, reorder point
- [x] Step 5: Delivery, logistics & warehouse performance analysis
- [x] Step 6: Demand forecasting & time series analysis
- [ ] Step 7: SQL database + business-question query library
- [ ] Step 8: Power BI dashboard (6 pages)
- [ ] Step 9: Business insights & recommendations report (30+ insights)
- [ ] Step 10: Resume bullets, LinkedIn post, dashboard screenshots
- [ ] Step 11: Interview prep bank (SQL / Python / Power BI / Supply Chain Analytics)

## Results & Business Impact (preview)

Once the SQL and Power BI layers are complete, this section will summarize projected impact — e.g., rebalancing warehouse capacity from the 135%/56% extremes, and tightening safety-stock policy against actual demand volatility rather than a flat assumption, both directly address findings already surfaced in the analysis above.

## Future Improvements

- Incorporate real weather/holiday-calendar features into the forecasting model
- Move from a flat safety-stock assumption to a per-SKU one based on observed demand variance
- Add supplier-level defect/on-time scorecards feeding into a Supplier Dashboard page

## License

MIT — see [LICENSE](LICENSE).
