# DAX Measures Library

All measures assume the data model relationships:
`fact_orders[product_id] → dim_products[product_id]`
`fact_orders[warehouse_id] → dim_warehouses[warehouse_id]`
`fact_orders[supplier_id] → dim_suppliers[supplier_id]`
`fact_orders[customer_id] → dim_customers[customer_id]`
`fact_orders[order_date] → dim_date[Date]`

Create a dedicated **Measures** table (New Table → blank) to keep these
organized and out of your data tables, then paste each measure below as a
New Measure on that table.

---

## Executive / core KPIs

```dax
Total Orders = COUNTROWS(fact_orders)

Total Revenue = SUM(fact_orders[selling_price])

Total Profit = SUM(fact_orders[profit])

Profit Margin % = DIVIDE([Total Profit], [Total Revenue], 0)

Total Orders (Valid) =
CALCULATE([Total Orders], fact_orders[order_status] <> "Cancelled")

Cancelled Orders % =
DIVIDE(
    CALCULATE([Total Orders], fact_orders[order_status] = "Cancelled"),
    [Total Orders], 0
)

Avg Order Value = DIVIDE([Total Revenue], [Total Orders (Valid)], 0)
```

## Delivery performance

```dax
Delivered Orders = CALCULATE([Total Orders], fact_orders[is_delivered] = 1)

On Time Deliveries =
CALCULATE([Total Orders], fact_orders[is_delivered] = 1, fact_orders[late_delivery_flag] = "No")

On Time Delivery % = DIVIDE([On Time Deliveries], [Delivered Orders], 0)

Late Deliveries =
CALCULATE([Total Orders], fact_orders[is_delivered] = 1, fact_orders[late_delivery_flag] = "Yes")

Avg Delivery Time (Days) =
CALCULATE(AVERAGE(fact_orders[order_to_delivery_days]), fact_orders[is_delivered] = 1)

Avg Delay (Late Orders Only) =
CALCULATE(AVERAGE(fact_orders[delivery_delay_days]), fact_orders[late_delivery_flag] = "Yes")

Perfect Order Rate =
VAR PerfectOrders =
    CALCULATE(
        [Total Orders],
        fact_orders[is_delivered] = 1,
        fact_orders[late_delivery_flag] = "No",
        fact_orders[return_flag] = "No"
    )
RETURN DIVIDE(PerfectOrders, [Total Orders (Valid)], 0)
```

## Inventory / fulfillment

```dax
Fill Rate = AVERAGE(fact_orders[fill_rate])

Backorders = CALCULATE([Total Orders], fact_orders[order_status] = "Backordered")

Stockout Rate = AVERAGE(fact_orders[stockout_flag])

Return Rate = DIVIDE(
    CALCULATE([Total Orders], fact_orders[return_flag] = "Yes"),
    [Total Orders (Valid)], 0
)

Order Fulfillment Rate =
DIVIDE(
    CALCULATE(SUM(fact_orders[stock_issued])),
    CALCULATE(SUM(fact_orders[order_quantity])),
    0
)

-- Current inventory position (latest reading per product/warehouse).
-- Requires a helper column or a calculated table -- see note below.
Inventory Value =
SUMX(
    fact_orders,
    fact_orders[inventory_level] * RELATED(dim_products[base_procurement_cost])
)
```
**Note on "current" inventory**: `inventory_level` is recorded per order
event, not per day, so a naive `SUM` double counts. For a true "as-of-today"
inventory figure, build a calculated table in Power Query that keeps only
the most recent `order_date` row per `(product_id, warehouse_id)` pair
(same logic as `Q7`/`Q9` in `sql/03_business_queries.sql`), then point
`Inventory Value` and `Warehouse Utilization %` at that table instead.

## Logistics / warehouse

```dax
Total Logistics Cost = SUM(fact_orders[shipping_cost])

Logistics Cost % of Revenue = DIVIDE([Total Logistics Cost], [Total Revenue], 0)

Avg Logistics Cost Per Order = DIVIDE([Total Logistics Cost], [Total Orders (Valid)], 0)

Total Warehouse Cost = SUM(fact_orders[warehouse_cost])

Warehouse Utilization % =
-- Point this at the "latest inventory per product/warehouse" table (see note above)
DIVIDE(
    SUM(fact_orders[inventory_level]),
    SUM(dim_warehouses[capacity_units]),
    0
)
```

## Forecast accuracy

```dax
Forecast Accuracy % = 100 - AVERAGE(fact_orders[forecast_error_pct])

MAPE = AVERAGE(fact_orders[forecast_error_pct])

Forecast Bias = AVERAGE(fact_orders[forecast_demand]) - AVERAGE(fact_orders[demand])
```

## Supplier performance

```dax
Avg Supplier Lead Time = AVERAGE(dim_suppliers[avg_lead_time_days])

Avg Supplier Defect Rate = AVERAGE(dim_suppliers[defect_rate])

Supplier Return Rate =
DIVIDE(
    CALCULATE([Total Orders], fact_orders[return_flag] = "Yes"),
    [Total Orders (Valid)], 0
)
```

## Time intelligence (requires dim_date marked as a Date table)

```dax
Revenue MTD = TOTALMTD([Total Revenue], dim_date[Date])

Revenue YTD = TOTALYTD([Total Revenue], dim_date[Date])

Revenue PY = CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(dim_date[Date]))

Revenue YoY % = DIVIDE([Total Revenue] - [Revenue PY], [Revenue PY], 0)

Revenue MoM % =
VAR CurrentMonth = [Total Revenue]
VAR PriorMonth = CALCULATE([Total Revenue], DATEADD(dim_date[Date], -1, MONTH))
RETURN DIVIDE(CurrentMonth - PriorMonth, PriorMonth, 0)
```
