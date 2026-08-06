# Resume Bullets (ATS-friendly)

- Engineered a 100,000-record supply chain analytics pipeline in Python (pandas, NumPy, statsmodels) simulating realistic order, inventory, and logistics data across 400 SKUs, 8 warehouses, and 25 suppliers, including chronological inventory-state modeling to ensure internal data consistency.
- Built inventory optimization models (ABC classification, EOQ, safety stock, reorder point) that identified a company-wide reorder-policy gap, validated across three independent methods (Python, SQL, and raw stockout data).
- Designed and implemented a star-schema SQL database (SQLite) with 5 dimension tables, 8 indexes, and a 15-query business intelligence library using CTEs, window functions, and views to answer core supply chain KPIs.
- Developed a demand forecasting workflow combining time-series decomposition and a custom seasonal-index model, improving holdout forecast accuracy from near 0% (naive trend model) to 82.1% (17.9% MAPE) on the hardest holiday-peak test window.
- Delivered a fully specified 6-page Power BI executive dashboard (35+ DAX measures, 18 KPIs, 18 visualization types) and a 34-insight business recommendations report translating raw data into prioritized, actionable operational decisions.
