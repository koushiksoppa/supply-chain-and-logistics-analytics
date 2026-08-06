-- ============================================================
-- 01_schema.sql
-- Star-schema design: one fact table (fact_orders) surrounded by
-- four dimension tables. Category is denormalized onto the fact
-- table (a common Kimball-style tradeoff) since it's filtered/grouped
-- on in nearly every query -- avoids a join for the single most-used
-- attribute while everything else stays properly normalized.
-- ============================================================

DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_warehouses;
DROP TABLE IF EXISTS dim_suppliers;
DROP TABLE IF EXISTS dim_customers;

CREATE TABLE dim_suppliers (
    supplier_id         TEXT PRIMARY KEY,
    supplier_name       TEXT NOT NULL,
    avg_lead_time_days  INTEGER NOT NULL,
    defect_rate         REAL NOT NULL,
    reliability_score   REAL NOT NULL
);

CREATE TABLE dim_warehouses (
    warehouse_id            TEXT PRIMARY KEY,
    region                   TEXT NOT NULL,
    hub_city                 TEXT NOT NULL,
    capacity_units           INTEGER NOT NULL,
    avg_processing_days      REAL NOT NULL,
    storage_cost_per_unit    REAL NOT NULL
);

CREATE TABLE dim_customers (
    customer_id       TEXT PRIMARY KEY,
    customer_region   TEXT NOT NULL,
    customer_city     TEXT NOT NULL
);

CREATE TABLE dim_products (
    product_id               TEXT PRIMARY KEY,
    product_name             TEXT NOT NULL,
    category                 TEXT NOT NULL,
    brand                    TEXT NOT NULL,
    base_procurement_cost    REAL NOT NULL,
    base_selling_price       REAL NOT NULL,
    daily_demand_rate        REAL NOT NULL,
    unit_weight_kg           REAL NOT NULL,
    supplier_id              TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES dim_suppliers(supplier_id)
);

CREATE TABLE fact_orders (
    order_id                TEXT PRIMARY KEY,
    customer_id             TEXT NOT NULL,
    product_id              TEXT NOT NULL,
    category                TEXT NOT NULL,   -- denormalized from dim_products
    warehouse_id            TEXT NOT NULL,
    region                  TEXT NOT NULL,
    supplier_id             TEXT NOT NULL,

    order_date               TEXT NOT NULL,
    ship_date                 TEXT,
    delivery_date              TEXT,

    inventory_level    REAL,
    demand              INTEGER,
    stock_received       REAL,
    stock_issued          REAL,

    transportation_mode    TEXT,
    carrier                 TEXT,
    distance_km              REAL,

    delivery_status    TEXT,
    order_status         TEXT,
    order_quantity        INTEGER,

    selling_price        REAL,
    procurement_cost       REAL,
    shipping_cost            REAL,
    warehouse_cost             REAL,
    total_cost                  REAL,
    profit                        REAL,
    profit_margin_pct               REAL,

    return_flag           TEXT,
    late_delivery_flag      TEXT,
    forecast_demand           INTEGER,
    forecast_error_pct          REAL,

    is_delivered           INTEGER,   -- boolean 0/1
    order_to_ship_days       REAL,
    order_to_delivery_days     REAL,
    delivery_delay_days          REAL,
    fill_rate                      REAL,
    stockout_flag                    INTEGER,  -- boolean 0/1

    order_year      INTEGER,
    order_month        INTEGER,
    order_quarter         INTEGER,

    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id),
    FOREIGN KEY (warehouse_id) REFERENCES dim_warehouses(warehouse_id),
    FOREIGN KEY (supplier_id) REFERENCES dim_suppliers(supplier_id)
);

-- Indexes on the columns actually filtered/grouped/joined on in the query
-- library below -- not indexing everything, just what's used.
CREATE INDEX idx_fact_orders_date ON fact_orders(order_date);
CREATE INDEX idx_fact_orders_warehouse ON fact_orders(warehouse_id);
CREATE INDEX idx_fact_orders_product ON fact_orders(product_id);
CREATE INDEX idx_fact_orders_supplier ON fact_orders(supplier_id);
CREATE INDEX idx_fact_orders_category ON fact_orders(category);
CREATE INDEX idx_fact_orders_region ON fact_orders(region);
CREATE INDEX idx_fact_orders_carrier ON fact_orders(carrier);
CREATE INDEX idx_fact_orders_status ON fact_orders(order_status);
