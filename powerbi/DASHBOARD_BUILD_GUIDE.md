# Power BI Dashboard Build Guide

## 1. Setup

1. Open Power BI Desktop → **Get Data → Text/CSV** → import all 6 files from `powerbi/data/`: `fact_orders.csv`, `dim_products.csv`, `dim_warehouses.csv`, `dim_suppliers.csv`, `dim_customers.csv`, `dim_date.csv`.
2. In **Model view**, create relationships (drag field to field):
   - `fact_orders[product_id]` → `dim_products[product_id]`
   - `fact_orders[warehouse_id]` → `dim_warehouses[warehouse_id]`
   - `fact_orders[supplier_id]` → `dim_suppliers[supplier_id]`
   - `fact_orders[customer_id]` → `dim_customers[customer_id]`
   - `fact_orders[order_date]` → `dim_date[Date]`
   - All should default to **one-to-many, single direction** (dimension → fact). See the star schema diagram shared in chat.
3. Right-click `dim_date` → **Mark as date table**, using the `Date` column.
4. Create a new table called **Measures** (Model view → New Table → `Measures = {BLANK()}`), then paste in every measure from `DAX_measures.md`.
5. Set data types: all `*_date` and `Date` columns → Date; `*_flag` columns → Text; `is_delivered`/`stockout_flag` → Whole Number (already 0/1).

## 2. Page 1 — Executive Dashboard

**Purpose**: One-glance company health for leadership.

| Visual | Fields | Notes |
|---|---|---|
| KPI Cards (5) | Total Orders, Total Revenue, Total Profit, Profit Margin %, On Time Delivery % | Top row, full width |
| Line chart | dim_date[Month Year] (axis), Total Revenue + Total Profit (values) | Shows the Nov/Dec seasonal spike |
| Treemap | category (group), Total Revenue (values) | Category revenue concentration |
| Waterfall chart | Category axis: Revenue → Procurement Cost → Shipping Cost → Warehouse Cost → Profit | Build via a small bridge table, or use the built-in Waterfall visual with `category` as breakdown and `profit` as values |
| Bar chart | region (axis), Total Revenue (values) | Sorted descending |
| Slicers | dim_date[Year Quarter], region, category | Sync across all pages via **Sync slicers** pane |

## 3. Page 2 — Inventory Dashboard

**Purpose**: Stock health, ABC classification, reorder risk.

| Visual | Fields | Notes |
|---|---|---|
| KPI Cards | Fill Rate, Stockout Rate, Backorders, Inventory Value | |
| Import `data/processed/inventory_analytics.csv` as an extra table | ABC Class, EOQ, Safety Stock, Reorder Point, Reorder Needed | This is Step 4's output — import it directly rather than recomputing in DAX |
| Treemap | ABC Class (group), Total Revenue (values) | Visualizes the 70/20/10 Pareto split |
| Matrix table | product_name (rows), ABC Class / EOQ / Safety Stock / Reorder Point / Latest Inventory Level (values) | Conditional formatting: red background where `Reorder Needed = TRUE` |
| Gauge chart | Fill Rate measure, target = 90% | |
| Scatter plot | Demand Std Dev (x), Avg Daily Demand (y), size = Total Revenue, color = ABC Class | From `inventory_analytics.csv` |
| Drill-through | Set up a **Product Detail** page; right-click any product row → Drill through | Shows that product's order history, delivery performance, and forecast |

## 4. Page 3 — Warehouse Dashboard

**Purpose**: Where the network is over/under capacity, and how well each warehouse executes.

| Visual | Fields | Notes |
|---|---|---|
| Map (Bing/ArcGIS) | dim_warehouses[hub_city] (location), Total Orders (size) | Plots the 5 fulfillment hubs |
| Bar chart | warehouse_id (axis), Warehouse Utilization % (values) | Reference line at 100% |
| Stacked column chart | warehouse_id (axis), order_status (legend), count of orders (values) | Shows Delivered/Cancelled/Returned mix per warehouse |
| KPI Cards | Perfect Order Rate, Avg Processing Days | |
| Heatmap (Matrix with conditional formatting) | warehouse_id (rows), dim_date[Month Name] (columns), On Time Delivery % (values, color scale) | Built-in Matrix visual with background color rules — no custom visual needed |
| Ribbon chart | dim_date[Year Quarter] (axis), warehouse_id (legend), Total Revenue (values) | Shows warehouse rank changes over time |
| Tooltips | Add a tooltip page showing Region, Hub City, Capacity, Current Units on hover over any warehouse visual | Report → New Page → set Page type = Tooltip |

## 5. Page 4 — Logistics Dashboard

**Purpose**: Cost and delay drivers across carriers, modes, and routes.

| Visual | Fields | Notes |
|---|---|---|
| KPI Cards | Total Logistics Cost, Logistics Cost % of Revenue, On Time Delivery %, Late Deliveries | |
| Bar chart | carrier (axis), Total Logistics Cost (values) | |
| Bar chart | transportation_mode (axis), Avg Logistics Cost Per Order (values) | Shows Air >> Sea/Rail cost gap |
| Line chart | dim_date[Month Year] (axis), Late Deliveries (values) | Trend over time |
| Decomposition tree | Total Logistics Cost (analyze), region → carrier → transportation_mode (explain by) | Lets viewers drill top-down interactively |
| Map | region (location), Late Deliveries (size), colored by On Time Delivery % | |
| Tooltips | Distance, Carrier, Mode shown on hover over any bar | |

## 6. Page 5 — Forecast Dashboard

**Purpose**: How good the demand forecast is, and where it's weakest.

| Visual | Fields | Notes |
|---|---|---|
| KPI Cards | Forecast Accuracy %, MAPE, Forecast Bias | |
| Line chart with built-in Forecast | dim_date[Date] (axis), Total Demand or `demand` (values) | Format pane → Analytics → Forecast → add forecast line with confidence band (Power BI's native forecasting, exponential smoothing under the hood) |
| Bar chart | category (axis), Forecast Accuracy % (values) | Import `forecast_accuracy.csv` for a ready-made version of this |
| Import `monthly_trends.csv` and `demand_forecast_next_quarter.csv` | | These already contain the Step 6 Python forecast — show alongside Power BI's own native forecast for comparison |
| Scatter plot | Avg Actual Demand (x), Avg Forecast Demand (y) per category | Points near the diagonal = accurate forecasts |

## 7. Page 6 — Supplier Dashboard

**Purpose**: Supplier reliability and its downstream impact.

| Visual | Fields | Notes |
|---|---|---|
| Matrix table | supplier_name (rows), Avg Supplier Lead Time, Avg Supplier Defect Rate, Reliability Score, Supplier Return Rate (values) | |
| Scatter plot | Reliability Score (x), Supplier Return Rate (y), size = order count | Outliers (low reliability, high actual returns) stand out |
| Bar chart | supplier_name (axis, top 10 by orders), Total Orders (values) | |
| KPI Cards | Avg Supplier Lead Time, Avg Supplier Defect Rate | |
| Bookmarks | Create two bookmarks: "All Suppliers" and "Top 10 by Volume" (filtered) with a toggle button group | Bookmarks pane → capture current filter state |

## 8. Cross-page features checklist

Every visual type from the original spec is covered somewhere above:
Bar ✓ (Pg 1,3,4,6) · Line ✓ (Pg 1,4,5) · Stacked ✓ (Pg 3) · Treemap ✓ (Pg 1,2) · Heatmap ✓ (Pg 3) · Map ✓ (Pg 3,4) · Matrix ✓ (Pg 2,3,6) · Scatter ✓ (Pg 2,5,6) · Ribbon ✓ (Pg 3) · Decomposition tree ✓ (Pg 4) · Waterfall ✓ (Pg 1) · KPI cards ✓ (every page) · Gauge ✓ (Pg 2) · Forecast visual ✓ (Pg 5) · Slicers ✓ (Pg 1, synced) · Bookmarks ✓ (Pg 6) · Drill-through ✓ (Pg 2) · Tooltips ✓ (Pg 3,4)

## 9. Export screenshots for the README

Once built, export each page as an image (File → Export → PDF, then screenshot each page, or use **View → Page view → Fit to page** and Win+Shift+S) and save to `images/dashboard_screenshots/`. These get embedded in the final README (Step 10).
