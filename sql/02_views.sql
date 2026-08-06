-- ============================================================
-- 02_views.sql
-- Reusable views so downstream queries (and Power BI, later) don't
-- have to repeat the same CASE/join logic every time.
-- ============================================================

-- View 1: Only orders that actually represent real business activity
-- (excludes cancelled orders, which never generated revenue or shipped)
DROP VIEW IF EXISTS vw_valid_orders;
CREATE VIEW vw_valid_orders AS
SELECT *
FROM fact_orders
WHERE order_status != 'Cancelled';

-- View 2: Order-level financial summary with a CASE-based margin tier,
-- demonstrating CASE WHEN in a reusable place
DROP VIEW IF EXISTS vw_order_financials;
CREATE VIEW vw_order_financials AS
SELECT
    order_id,
    product_id,
    category,
    warehouse_id,
    region,
    order_date,
    selling_price,
    total_cost,
    profit,
    profit_margin_pct,
    CASE
        WHEN profit_margin_pct >= 25 THEN 'High Margin'
        WHEN profit_margin_pct >= 10 THEN 'Medium Margin'
        WHEN profit_margin_pct >= 0  THEN 'Low Margin'
        ELSE 'Loss Making'
    END AS margin_tier
FROM fact_orders
WHERE order_status != 'Cancelled';

-- View 3: Delivered orders only, with delay classification
DROP VIEW IF EXISTS vw_delivery_performance;
CREATE VIEW vw_delivery_performance AS
SELECT
    order_id,
    warehouse_id,
    region,
    carrier,
    transportation_mode,
    order_date,
    delivery_date,
    order_to_delivery_days,
    delivery_delay_days,
    late_delivery_flag,
    CASE
        WHEN late_delivery_flag = 'No' THEN 'On Time'
        WHEN delivery_delay_days <= 2 THEN 'Slightly Late (1-2 days)'
        WHEN delivery_delay_days <= 5 THEN 'Late (3-5 days)'
        ELSE 'Severely Late (5+ days)'
    END AS delay_bucket
FROM fact_orders
WHERE is_delivered = 1;
