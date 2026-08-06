-- ============================================================
-- 03_business_queries.sql
-- Answers to the core business questions, using: SELECT, GROUP BY,
-- ORDER BY, CASE WHEN, WINDOW FUNCTIONS, CTEs, subqueries, and JOINs.
-- Each query is self-contained and commented with which techniques
-- it demonstrates.
-- ============================================================

-- --------------------------------------------------------------
-- Q1. Top performing warehouse by revenue and profit
-- Technique: JOIN, GROUP BY, ORDER BY
-- --------------------------------------------------------------
SELECT
    w.warehouse_id,
    w.region,
    w.hub_city,
    COUNT(f.order_id)              AS total_orders,
    ROUND(SUM(f.selling_price), 0) AS total_revenue,
    ROUND(SUM(f.profit), 0)        AS total_profit
FROM fact_orders f
JOIN dim_warehouses w ON f.warehouse_id = w.warehouse_id
WHERE f.order_status != 'Cancelled'
GROUP BY w.warehouse_id, w.region, w.hub_city
ORDER BY total_revenue DESC;


-- --------------------------------------------------------------
-- Q2. Highest logistics (shipping) cost by carrier and mode
-- Technique: GROUP BY, CASE WHEN, ORDER BY
-- --------------------------------------------------------------
SELECT
    carrier,
    transportation_mode,
    COUNT(*)                          AS shipments,
    ROUND(SUM(shipping_cost), 0)      AS total_shipping_cost,
    ROUND(AVG(shipping_cost), 1)      AS avg_shipping_cost,
    CASE
        WHEN AVG(shipping_cost) > 5000 THEN 'High Cost'
        WHEN AVG(shipping_cost) > 500  THEN 'Medium Cost'
        ELSE 'Low Cost'
    END AS cost_tier
FROM fact_orders
WHERE order_status != 'Cancelled'
GROUP BY carrier, transportation_mode
ORDER BY total_shipping_cost DESC
LIMIT 10;


-- --------------------------------------------------------------
-- Q3. Average delivery time overall and by region
-- Technique: GROUP BY with ROLLUP-style UNION for a grand total row
-- --------------------------------------------------------------
SELECT region, ROUND(AVG(order_to_delivery_days), 2) AS avg_delivery_days
FROM fact_orders
WHERE is_delivered = 1
GROUP BY region
UNION ALL
SELECT 'ALL REGIONS', ROUND(AVG(order_to_delivery_days), 2)
FROM fact_orders
WHERE is_delivered = 1
ORDER BY avg_delivery_days;


-- --------------------------------------------------------------
-- Q4. Fill rate by category
-- Technique: GROUP BY, ORDER BY
-- --------------------------------------------------------------
SELECT
    category,
    COUNT(*)                        AS orders,
    ROUND(AVG(fill_rate) * 100, 1)  AS avg_fill_rate_pct
FROM fact_orders
GROUP BY category
ORDER BY avg_fill_rate_pct ASC;


-- --------------------------------------------------------------
-- Q5. Inventory turnover proxy per product
-- (Total units sold / average inventory level -- classic turnover formula)
-- Technique: CTE, JOIN, subquery-style aggregation
-- --------------------------------------------------------------
WITH product_sales AS (
    SELECT product_id, SUM(order_quantity) AS units_sold
    FROM fact_orders
    WHERE order_status != 'Cancelled'
    GROUP BY product_id
),
product_avg_inventory AS (
    SELECT product_id, AVG(inventory_level) AS avg_inventory
    FROM fact_orders
    GROUP BY product_id
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    s.units_sold,
    ROUND(i.avg_inventory, 1)                                          AS avg_inventory,
    ROUND(s.units_sold * 1.0 / NULLIF(i.avg_inventory, 0), 2)          AS inventory_turnover_ratio
FROM product_sales s
JOIN product_avg_inventory i ON s.product_id = i.product_id
JOIN dim_products p ON s.product_id = p.product_id
ORDER BY inventory_turnover_ratio DESC
LIMIT 15;


-- --------------------------------------------------------------
-- Q6. Late delivery percentage by region and carrier
-- Technique: GROUP BY, CASE WHEN inside aggregate
-- --------------------------------------------------------------
SELECT
    region,
    carrier,
    COUNT(*)                                                              AS deliveries,
    SUM(CASE WHEN late_delivery_flag = 'Yes' THEN 1 ELSE 0 END)           AS late_deliveries,
    ROUND(100.0 * SUM(CASE WHEN late_delivery_flag = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS late_pct
FROM fact_orders
WHERE is_delivered = 1
GROUP BY region, carrier
ORDER BY late_pct DESC
LIMIT 10;


-- --------------------------------------------------------------
-- Q7. Stock availability: current inventory position by warehouse
-- Technique: Window function (ROW_NUMBER) to get the latest inventory
-- reading per product/warehouse, then aggregate
-- --------------------------------------------------------------
WITH latest_inventory AS (
    SELECT
        warehouse_id,
        product_id,
        inventory_level,
        ROW_NUMBER() OVER (
            PARTITION BY warehouse_id, product_id
            ORDER BY order_date DESC
        ) AS rn
    FROM fact_orders
)
SELECT
    warehouse_id,
    COUNT(DISTINCT product_id)                                   AS products_stocked,
    SUM(CASE WHEN inventory_level <= 0 THEN 1 ELSE 0 END)        AS products_out_of_stock,
    ROUND(100.0 * SUM(CASE WHEN inventory_level <= 0 THEN 1 ELSE 0 END)
          / COUNT(DISTINCT product_id), 1)                       AS stockout_pct
FROM latest_inventory
WHERE rn = 1
GROUP BY warehouse_id
ORDER BY stockout_pct DESC;


-- --------------------------------------------------------------
-- Q8. Supplier performance: reliability vs. actual return rate
-- Technique: JOIN across fact + 2 dimensions, GROUP BY
-- --------------------------------------------------------------
SELECT
    s.supplier_id,
    s.supplier_name,
    s.reliability_score,
    s.defect_rate,
    s.avg_lead_time_days,
    COUNT(f.order_id)                                            AS orders_supplied,
    ROUND(100.0 * SUM(CASE WHEN f.return_flag = 'Yes' THEN 1 ELSE 0 END)
          / COUNT(f.order_id), 2)                                AS actual_return_rate_pct
FROM fact_orders f
JOIN dim_suppliers s ON f.supplier_id = s.supplier_id
GROUP BY s.supplier_id, s.supplier_name, s.reliability_score, s.defect_rate, s.avg_lead_time_days
ORDER BY actual_return_rate_pct DESC
LIMIT 10;


-- --------------------------------------------------------------
-- Q9. Warehouse utilization (current inventory units vs. capacity)
-- Technique: CTE + window function + JOIN
-- --------------------------------------------------------------
WITH latest_inventory AS (
    SELECT
        warehouse_id,
        product_id,
        inventory_level,
        ROW_NUMBER() OVER (
            PARTITION BY warehouse_id, product_id
            ORDER BY order_date DESC
        ) AS rn
    FROM fact_orders
),
warehouse_inventory AS (
    SELECT warehouse_id, SUM(inventory_level) AS current_units
    FROM latest_inventory
    WHERE rn = 1
    GROUP BY warehouse_id
)
SELECT
    w.warehouse_id,
    w.hub_city,
    w.capacity_units,
    ROUND(wi.current_units, 0)                                   AS current_units,
    ROUND(100.0 * wi.current_units / w.capacity_units, 1)        AS utilization_pct
FROM warehouse_inventory wi
JOIN dim_warehouses w ON wi.warehouse_id = w.warehouse_id
ORDER BY utilization_pct DESC;


-- --------------------------------------------------------------
-- Q10. Monthly sales trend with month-over-month growth
-- Technique: Window function (LAG) for period-over-period comparison
-- --------------------------------------------------------------
WITH monthly_sales AS (
    SELECT
        strftime('%Y-%m', order_date) AS sales_month,
        SUM(selling_price)            AS monthly_revenue
    FROM fact_orders
    WHERE order_status != 'Cancelled'
    GROUP BY sales_month
)
SELECT
    sales_month,
    ROUND(monthly_revenue, 0)                                                    AS monthly_revenue,
    ROUND(monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY sales_month), 0)  AS revenue_change,
    ROUND(100.0 * (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY sales_month))
          / LAG(monthly_revenue) OVER (ORDER BY sales_month), 1)                 AS mom_growth_pct
FROM monthly_sales
ORDER BY sales_month;


-- --------------------------------------------------------------
-- Q11. Most expensive shipping routes (Region x Carrier x Mode)
-- Technique: GROUP BY multiple columns, HAVING with subquery for a
-- data-driven minimum sample size (avoids noisy low-volume combos)
-- --------------------------------------------------------------
SELECT
    region,
    carrier,
    transportation_mode,
    COUNT(*)                     AS shipments,
    ROUND(AVG(distance_km), 0)   AS avg_distance_km,
    ROUND(AVG(shipping_cost), 0) AS avg_shipping_cost
FROM fact_orders
WHERE order_status != 'Cancelled'
GROUP BY region, carrier, transportation_mode
HAVING COUNT(*) > (SELECT COUNT(*) * 1.0 / 300 FROM fact_orders)  -- exclude tiny/noisy route combos
ORDER BY avg_shipping_cost DESC
LIMIT 10;


-- --------------------------------------------------------------
-- Q12. Top delayed regions, ranked
-- Technique: Window function RANK()
-- --------------------------------------------------------------
SELECT
    region,
    late_pct,
    RANK() OVER (ORDER BY late_pct DESC) AS delay_rank
FROM (
    SELECT
        region,
        ROUND(100.0 * SUM(CASE WHEN late_delivery_flag = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS late_pct
    FROM fact_orders
    WHERE is_delivered = 1
    GROUP BY region
);


-- --------------------------------------------------------------
-- Q13. Category-wise profit and margin
-- Technique: GROUP BY, ORDER BY, ROUND
-- --------------------------------------------------------------
SELECT
    category,
    COUNT(*)                                       AS orders,
    ROUND(SUM(selling_price), 0)                   AS total_revenue,
    ROUND(SUM(profit), 0)                          AS total_profit,
    ROUND(AVG(profit_margin_pct), 1)               AS avg_margin_pct
FROM fact_orders
WHERE order_status != 'Cancelled'
GROUP BY category
ORDER BY total_profit DESC;


-- --------------------------------------------------------------
-- Q14. Transportation cost by carrier as % of total logistics spend
-- Technique: Window function for share-of-total (SUM() OVER ())
-- --------------------------------------------------------------
SELECT
    carrier,
    ROUND(SUM(shipping_cost), 0)                                              AS carrier_cost,
    ROUND(100.0 * SUM(shipping_cost) / SUM(SUM(shipping_cost)) OVER (), 1)    AS pct_of_total_logistics_cost
FROM fact_orders
WHERE order_status != 'Cancelled'
GROUP BY carrier
ORDER BY carrier_cost DESC;


-- --------------------------------------------------------------
-- Q15. ABC-style top revenue products with cumulative share
-- Technique: Window functions (SUM OVER for running total, PERCENT_RANK)
-- --------------------------------------------------------------
WITH product_revenue AS (
    SELECT
        p.product_id,
        p.product_name,
        SUM(f.selling_price) AS revenue
    FROM fact_orders f
    JOIN dim_products p ON f.product_id = p.product_id
    WHERE f.order_status != 'Cancelled'
    GROUP BY p.product_id, p.product_name
)
SELECT
    product_id,
    product_name,
    ROUND(revenue, 0)                                                            AS revenue,
    ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER (), 1) AS cumulative_revenue_pct
FROM product_revenue
ORDER BY revenue DESC
LIMIT 20;
