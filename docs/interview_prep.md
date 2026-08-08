# Interview Preparation Bank

110 questions across SQL, Power BI, Python, and Supply Chain Analytics.
Where relevant, answers reference this project specifically — use those as
your own talking points, not just the general explanation.

---

## SQL (30 Questions)

**1. What's the difference between WHERE and HAVING?**
`WHERE` filters rows before grouping; `HAVING` filters groups after aggregation. In `sql/03_business_queries.sql` Q11, `HAVING COUNT(*) > (subquery)` filters out low-volume route combinations *after* grouping — `WHERE` couldn't do that since `COUNT(*)` doesn't exist until grouping happens.

**2. Explain the difference between INNER JOIN, LEFT JOIN, and FULL OUTER JOIN.**
INNER JOIN returns only matching rows from both tables. LEFT JOIN returns all rows from the left table plus matches from the right (NULL where no match). FULL OUTER JOIN returns all rows from both, matched where possible. This project's `load_to_sql.py` sanity check uses a LEFT JOIN specifically to find orphaned foreign keys (rows in `fact_orders` with no matching `dim_products` row) — the NULLs are the signal.

**3. What is a CTE and why use one over a subquery?**
A Common Table Expression (`WITH x AS (...)`) is a named, temporary result set scoped to one query. It's more readable than nested subqueries and can be referenced multiple times. Q5 in this project's query library uses two CTEs (`product_sales`, `product_avg_inventory`) to compute inventory turnover — doing this as nested subqueries would be much harder to read.

**4. What's a window function, and how does it differ from GROUP BY?**
GROUP BY collapses rows into one row per group. A window function (`OVER (...)`) computes an aggregate or ranking *without* collapsing rows — each row keeps its detail plus the calculated value. Q10 uses `LAG()` to compute month-over-month revenue growth while keeping every month as its own row.

**5. Explain ROW_NUMBER(), RANK(), and DENSE_RANK().**
All three assign a rank within a partition, ordered by some column. ROW_NUMBER() gives unique sequential numbers even on ties. RANK() gives the same rank to ties but skips the next number(s). DENSE_RANK() gives the same rank to ties without skipping. Q7 in this project uses ROW_NUMBER() partitioned by product+warehouse, ordered by date descending, to isolate just the latest inventory reading per pair.

**6. What does PARTITION BY do inside a window function?**
It resets the window function's calculation for each group, similar to GROUP BY but without collapsing rows. `ROW_NUMBER() OVER (PARTITION BY warehouse_id, product_id ORDER BY order_date DESC)` restarts the numbering for every warehouse/product combination.

**7. How would you find the top N rows per group in SQL?**
Wrap a `ROW_NUMBER() OVER (PARTITION BY group_col ORDER BY metric DESC)` in a CTE, then filter `WHERE rn <= N` in the outer query. This is exactly the pattern used to get "latest inventory reading per product/warehouse" in Q7/Q9.

**8. What is a star schema, and why use one?**
A central fact table (transactional, numeric, high volume) surrounded by dimension tables (descriptive attributes, low volume). It's optimized for BI/analytical queries — fewer joins, clear separation of "what happened" from "who/what/where." This project's `fact_orders` table sits at the center with `dim_products`, `dim_warehouses`, `dim_suppliers`, `dim_customers` around it.

**9. When would you denormalize a column onto a fact table?**
When that attribute is filtered/grouped on in nearly every query and the join cost outweighs the redundancy cost. This project denormalizes `category` onto `fact_orders` even though it technically belongs to `dim_products`, since almost every business question groups by category.

**10. What's the purpose of an index, and when might it hurt performance?**
An index speeds up lookups/filters/joins on a column by avoiding a full table scan. It costs extra storage and slows down writes (INSERT/UPDATE must update the index too). This project indexes `order_date`, `warehouse_id`, `product_id`, `category`, etc. — the columns actually used in the query library's WHERE/GROUP BY/JOIN clauses, not every column.

**11. What's a foreign key, and what does it guarantee?**
A column (or set of columns) that references a primary key in another table, enforcing referential integrity — you can't insert a fact row pointing to a dimension row that doesn't exist. This project validates that guarantee post-load with an explicit orphan-check query.

**12. Explain the difference between UNION and UNION ALL.**
UNION removes duplicate rows across the combined result sets (requires a sort/dedup step); UNION ALL keeps everything, including duplicates, and is faster. Q3 in this project uses UNION ALL to append a grand-total "ALL REGIONS" row to per-region averages.

**13. What is a view, and how is it different from a table?**
A view is a saved query that behaves like a virtual table — it doesn't store data itself (unless materialized), it re-runs its underlying query each time. This project's `vw_delivery_performance` view encapsulates a CASE-based delay-bucket classification so downstream queries don't have to repeat that logic.

**14. How would you calculate a running total in SQL?**
`SUM(column) OVER (ORDER BY date_col)` — a window function with no PARTITION BY (or partitioned by the relevant group) accumulates the sum as it moves through the ordered rows. This project's ABC-classification query (Q15) uses this pattern to compute cumulative revenue share.

**15. What's the difference between a scalar subquery and a correlated subquery?**
A scalar subquery returns a single value and can run independently. A correlated subquery references a column from the outer query, so it re-runs conceptually once per outer row. Q11's HAVING clause uses a simple scalar subquery (`SELECT COUNT(*) * 1.0/300 FROM fact_orders`) since it doesn't depend on the outer query's grouping.

**16. How do you handle NULLs in aggregate calculations?**
Most aggregate functions (SUM, AVG, COUNT(column)) ignore NULLs automatically. `COUNT(*)` counts all rows including NULLs. Division by a potentially-NULL/zero denominator should use `NULLIF()` to avoid errors — used in Q5's inventory turnover ratio (`NULLIF(avg_inventory, 0)`).

**17. What's the difference between DELETE, TRUNCATE, and DROP?**
DELETE removes rows (can be filtered, logged, rolled back). TRUNCATE removes all rows fast, resets identity, minimal logging. DROP removes the entire table structure. `01_schema.sql` uses `DROP TABLE IF EXISTS` to make the schema script safely re-runnable.

**18. How would you find duplicate rows in a table?**
`GROUP BY` the columns that should be unique, `HAVING COUNT(*) > 1`. Alternatively, a window function `ROW_NUMBER() OVER (PARTITION BY key_cols ORDER BY key_cols) ` and filter `rn > 1`.

**19. What is query execution order in SQL (conceptually)?**
FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT. This is why you can't reference a SELECT alias in a WHERE clause (WHERE runs before SELECT is evaluated) but you can in ORDER BY.

**20. How would you calculate month-over-month or year-over-year growth in SQL?**
`LAG(metric) OVER (ORDER BY period)` to pull the prior period's value into the same row, then compute the percentage difference. Exactly Q10's pattern for monthly revenue growth.

**21. What's the difference between a clustered and non-clustered index?**
A clustered index determines the physical storage order of table rows (one per table). A non-clustered index is a separate structure pointing back to the row location (many allowed per table). SQLite doesn't have true clustered indexes outside of `INTEGER PRIMARY KEY` (rowid), but the concept transfers to Postgres/SQL Server for a production version of this schema.

**22. How do you optimize a slow query?**
Check the execution plan (`EXPLAIN QUERY PLAN` in SQLite), look for full table scans on large tables, add indexes on filtered/joined columns, avoid `SELECT *`, and ensure JOINs use indexed columns. This project's indexes were chosen by first writing the query library, then indexing exactly the columns those 15 queries touch.

**23. What's a self-join and when would you use one?**
A table joined to itself, typically to compare rows within the same table — e.g., finding employees earning more than their manager. Not used directly in this project's schema, but a natural extension would be comparing a warehouse's current-month performance to its own prior-month row.

**24. Explain the difference between WHERE clause filtering and JOIN condition filtering.**
Filtering in the JOIN's ON clause happens *before* the join completes (affects which rows get matched, especially in LEFT JOINs); filtering in WHERE happens *after*. Put a LEFT JOIN's filter in ON to keep unmatched rows; put it in WHERE and you'll silently convert it into an INNER JOIN.

**25. What is referential integrity, and how did you validate it in this project?**
The guarantee that foreign key references always point to an existing row. Validated with a `LEFT JOIN ... WHERE dim.pk IS NULL` orphan check in `load_to_sql.py`, confirming 0 orphaned `product_id` references after loading 100,000 rows.

**26. How would you calculate a percentile in SQL?**
Depends on the engine — Postgres has `PERCENTILE_CONT`, SQLite doesn't have a native function so you'd compute it via `NTILE()` or a manual ordered-row-position calculation. Worth mentioning as a known SQLite limitation if asked.

**27. What's the difference between IN and EXISTS?**
`IN` compares a value against a list/subquery result. `EXISTS` checks whether a correlated subquery returns any rows, and can be more efficient for large subqueries since it can short-circuit on the first match.

**28. How do you handle date arithmetic in SQL?**
SQLite uses `strftime()`/`julianday()` for date manipulation and formatting — Q10 uses `strftime('%Y-%m', order_date)` to bucket orders into calendar months. Other engines (Postgres, SQL Server) have their own date functions (`DATE_TRUNC`, `DATEADD`).

**29. What's the difference between a fact table and a dimension table?**
A fact table holds quantitative, transactional data (usually numeric, one row per event) with foreign keys to dimensions. A dimension table holds descriptive, relatively static attributes. `fact_orders` (100,000 rows, one per order) vs. `dim_products` (400 rows, describing what a product is).

**30. How would you answer "what's our on-time delivery rate by region" as a SQL query, out loud?**
"I'd filter to delivered orders only, group by region, then use a CASE-inside-SUM to count late deliveries, divide by total deliveries, and multiply by 100 — that's exactly Q6 in the project." Practicing saying the query out loud, not just writing it, is what interviewers are actually testing.

---

## Power BI (30 Questions)

**31. What's the difference between a calculated column and a measure?**
A calculated column is computed row-by-row at data-refresh time and stored in the model (uses row context). A measure is computed on-the-fly at query time based on the current filter context (uses filter context) and isn't stored. Nearly everything in `DAX_measures.md` is a measure — e.g., `Total Revenue` recalculates instantly as slicers change, rather than being a fixed per-row value.

**32. Explain filter context vs. row context in DAX.**
Row context is "which row am I currently on" (relevant inside calculated columns and iterator functions like SUMX). Filter context is "which set of rows is currently visible" based on slicers, visual-level filters, and relationships (relevant to measures). `CALCULATE()` is the function that lets you modify filter context explicitly.

**33. What does CALCULATE() do, and why is it central to DAX?**
It evaluates an expression within a modified filter context — you pass it a base expression plus one or more filter conditions that override or add to the current context. Nearly every conditional measure in this project (`On Time Deliveries`, `Delivered Orders`) uses `CALCULATE()` to apply a specific filter (e.g., `is_delivered = 1`) on top of whatever the report's slicers already filter.

**34. What's the difference between SUM() and SUMX()?**
`SUM()` aggregates a single column directly. `SUMX()` iterates row-by-row over a table, evaluating an expression per row, then sums the results — needed when the calculation itself requires row-level logic. `Inventory Value` in this project uses `SUMX` because it multiplies `inventory_level` by a *related* column (`base_procurement_cost`) row by row.

**35. How do relationships work in Power BI's data model, and what's cardinality?**
Relationships connect tables via a common key, propagating filters between them. Cardinality describes the match pattern: one-to-many (most common — one dimension row matches many fact rows), one-to-one, or many-to-many. This project's model is entirely one-to-many, dimension-to-fact, single filter direction.

**36. What's the difference between single-direction and bi-directional filtering?**
Single-direction: filtering a dimension filters the fact table, but not vice versa (the default, safest choice). Bi-directional: filters propagate both ways, which can cause ambiguous filter paths in complex models. This project deliberately keeps every relationship single-direction to avoid that ambiguity.

**37. What is a Date table, and why mark one explicitly?**
A dedicated table of contiguous dates (no gaps) used for time-intelligence functions (`TOTALYTD`, `SAMEPERIODLASTYEAR`, etc.). Marking it as a Date table tells Power BI which column is the actual date axis, enabling those functions to work correctly. `dim_date.csv` in this project spans 2024-01-01 through 2026-03-31 (covering the forecast horizon too) precisely so time-intelligence measures work without gaps.

**38. Explain TOTALYTD, TOTALMTD, and SAMEPERIODLASTYEAR.**
These are DAX time-intelligence shortcuts. `TOTALYTD`/`TOTALMTD` accumulate a measure from the start of the year/month to the current date in context. `SAMEPERIODLASTYEAR` shifts the current filter context back exactly one year, letting you compare the same measure period-over-period — used in this project's `Revenue YoY %` measure.

**39. What's the difference between a Treemap and a Bar chart, and when would you choose one over the other?**
A bar chart is best for precise magnitude comparison across categories. A treemap shows part-to-whole relationships and hierarchy via nested rectangle area, better for "how much of the total does each category represent" at a glance. This project uses a treemap on the Executive page for revenue-by-category (part-to-whole) and a bar chart on the Warehouse page for utilization (precise comparison).

**40. What's a Decomposition Tree used for?**
An interactive visual that lets the user drill top-down into what's driving a metric, choosing which dimension to break down by at each level, without pre-defining the hierarchy. Used on the Logistics page in this project's dashboard spec to let a viewer explore Total Logistics Cost by region → carrier → mode interactively.

**41. How does Power BI's built-in Forecast feature work?**
It's available in the Analytics pane on line charts — it applies exponential smoothing to the historical series and projects forward with a confidence interval band. It's a black-box convenience feature; this project pairs it with a transparent, custom-built Python seasonal-index forecast (`demand_forecast_next_quarter.csv`) specifically so the methodology is inspectable, not just a built-in line.

**42. What's the difference between a Slicer and a Filter pane filter?**
A slicer is a visible, interactive visual on the report canvas that end-users can click/select. A filter pane filter is set by the report author and can be hidden from end-users, or locked. Slicers are for end-user exploration; filter-pane filters are for report-author-controlled scoping.

**43. How do Bookmarks work, and what's a practical use case?**
A bookmark captures the current state of a report page — filters, slicer selections, visual visibility, even which object is in focus — and lets a button restore that exact state on click. Used on the Supplier page in this project to toggle between an "All Suppliers" view and a "Top 10 by Volume" filtered view without needing two separate pages.

**44. What is Drill-through, and how is it different from Drill-down?**
Drill-down moves through a hierarchy within the same visual (e.g., Category → Product). Drill-through jumps to an entirely different report page, pre-filtered to the context you right-clicked from. This project uses drill-through from the Inventory page's product matrix to a dedicated Product Detail page.

**45. What's the purpose of a Tooltip page in Power BI?**
A regular report page set to "Tooltip" type, shown when hovering over a data point on another visual instead of the default single-value tooltip — lets you show a mini-report (multiple KPIs, a small chart) on hover. Used on the Warehouse and Logistics pages in this project to show region/carrier/distance detail on hover.

**46. Why would you use a Matrix visual with conditional formatting instead of a table?**
A Matrix supports row/column hierarchies and cross-tabulation (like a pivot table), and conditional formatting can turn cell backgrounds into a heatmap directly. Used on the Warehouse page in this project (warehouse × month, colored by on-time %) — avoiding the need for a separate heatmap custom visual.

**47. What's the difference between DirectQuery and Import mode?**
Import mode loads a compressed copy of the data into Power BI's in-memory engine (fast, but requires refresh to update). DirectQuery sends live queries to the source on every interaction (always current, but slower and dependent on source performance). This project uses Import mode since the CSVs are static outputs of an offline Python pipeline.

**48. How would you handle a many-to-many relationship in Power BI?**
Either mark the relationship as many-to-many directly (supported natively but can hurt performance) or introduce a bridge table between the two entities. Not present in this project's schema (every relationship is a clean one-to-many), but worth knowing as a follow-up question.

**49. What is DAX's evaluation context, and why does the same measure return different values on different visuals?**
Because measures are recalculated per-cell based on that cell's filter context (row/column headers, slicer selections, page filters). The same `[Total Revenue]` measure returns a different number in a matrix cell filtered to one warehouse vs. the report-level total, without changing the formula.

**50. What's the difference between COUNT, COUNTA, COUNTROWS, and DISTINCTCOUNT?**
`COUNT` counts numeric values in a column (ignoring blanks). `COUNTA` counts non-blank values of any type. `COUNTROWS` counts rows in a table (used for `Total Orders` in this project). `DISTINCTCOUNT` counts unique values in a column.

**51. How do you optimize a slow Power BI report?**
Reduce cardinality of high-distinct-value columns, avoid bidirectional relationships where not needed, prefer measures over calculated columns where possible, limit the number of visuals per page, and use Import mode over DirectQuery where feasible. Performance Analyzer (View ribbon) shows exactly which visual is slow and why.

**52. What's the difference between a KPI card and a Gauge visual?**
A card shows a single number, optionally with a trend indicator. A gauge shows a value against a target/min/max range visually, better for "are we above or below target" at a glance. This project uses a gauge specifically for Fill Rate against a 90% target on the Inventory page.

**53. Explain the star schema's role in Power BI performance specifically.**
Power BI's VertiPaq engine is optimized for star schemas — fewer, simpler joins mean faster filter propagation and smaller compressed model size. A snowflaked (over-normalized) or flat (fully denormalized) model both perform worse than a clean star schema for typical BI query patterns.

**54. What's a calculated table, and when would you use one?**
A table generated by a DAX expression rather than imported directly, recalculated on refresh. This project's build guide flags one specific need for it: a "latest inventory reading per product/warehouse" table, since the raw fact table has one row per order event, not per current state.

**55. How does RLS (Row-Level Security) work in Power BI?**
You define DAX filter expressions per role (e.g., `[Region] = USERNAME()`) that restrict which rows a given user can see when they open the report, enforced at the data model level so it can't be bypassed by removing a visual-level filter.

**56. What's the difference between implicit and explicit measures?**
Implicit measures are auto-generated when you drag a numeric column directly into a visual's Values well (Power BI silently wraps it in SUM/AVG/etc.). Explicit measures are ones you define yourself in DAX. This project's whole `DAX_measures.md` library is explicit measures — recommended practice for any report meant to be maintained or extended.

**57. How would you show "% of total" in a visual (e.g., each category's share of total revenue)?**
`DIVIDE([Total Revenue], CALCULATE([Total Revenue], ALL(dim_products[category])), 0)` — the `ALL()` function removes the category filter just for the denominator, giving you the grand total to divide against.

**58. What is ALL() used for in DAX?**
It removes filters from a table or column, letting you calculate against an unfiltered baseline even inside a filtered context — essential for percent-of-total, ranking, and "compare to overall average" calculations.

**59. What's the difference between a Ribbon chart and a stacked column chart?**
Both show composition over time/category, but a Ribbon chart specifically emphasizes rank changes between categories over time with connecting ribbons — better for "who was #1 last quarter vs. this quarter" than a stacked column, which emphasizes absolute/relative magnitude at each point.

**60. How would you explain this project's data model to a non-technical stakeholder?**
"There's one big table of every order ever placed, and four smaller reference tables — what the product is, which warehouse it shipped from, who supplied it, and who bought it. Power BI connects them so when you click 'Grocery' on a filter, every chart on the page automatically updates to show only grocery orders."

---

## Python (30 Questions)

**61. Why use pandas' vectorized operations instead of iterating with a for loop?**
Vectorized operations run in compiled C under the hood across the whole array at once, instead of looping in interpreted Python row-by-row — often 10-100x faster. This project's dataset generator uses `np.where`, `np.random.Generator.choice` with weighted probabilities, and array broadcasting throughout `generate_dataset.py` for exactly this reason, reserving Python-level loops only for the one place that genuinely needs sequential state (the chronological inventory simulation).

**62. Why did the inventory simulation need a loop instead of a fully vectorized approach?**
Because each order's outcome (available inventory, whether a reorder fires) depends on the *running state* left by the previous order for that same product/warehouse — a genuinely sequential dependency that can't be vectorized away. The loop is scoped as tightly as possible (grouped by product+warehouse, ~4,000 small groups) rather than looping over all 100,000 rows unnecessarily.

**63. What's the difference between .loc[] and .iloc[] in pandas?**
`.loc[]` selects by label (index name or boolean mask). `.iloc[]` selects by integer position. Mixing them up is a common source of subtle bugs, especially after filtering or sorting changes what the "position" of a row actually is.

**64. Explain the difference between a Series and a DataFrame.**
A Series is a single labeled 1-D array (like one column with an index). A DataFrame is a 2-D table of Series sharing a common index — think of it as a dict of Series.

**65. What does groupby().agg() let you do that a simple groupby().mean() doesn't?**
`.agg()` lets you apply different aggregation functions to different columns in a single pass, and name the output columns explicitly — e.g., this project's warehouse performance analysis computes `count`, `sum`, and a custom lambda (late-delivery count) all in one `.agg()` call rather than three separate groupby operations.

**66. How do you handle missing data in pandas, and what's the difference between the strategies?**
`.dropna()` removes rows/columns with nulls (loses data). `.fillna()` imputes a value (mean, median, forward-fill, a constant). The right choice depends on *why* the value is missing. This project's `clean_and_engineer.py` explicitly distinguishes *structural* nulls (a cancelled order will never have a delivery date — that's not missing data, it's correct) from genuine data-quality nulls, handling each differently instead of blanket-imputing everything.

**67. What's the IQR method for outlier detection, and why compute it per group instead of globally?**
IQR = Q3 − Q1 (the interquartile range); outliers are typically flagged as anything beyond `Q1 - 1.5×IQR` or `Q3 + 1.5×IQR`. Computing it globally on a mixed-category dataset would flag nearly every high-value category (e.g., Electronics) as "outliers" relative to low-value categories (e.g., Grocery) — this project computes IQR separately within each product category so the comparison is apples-to-apples.

**68. Why flag outliers instead of deleting them?**
Because an extreme value might be a real business event (a large bulk B2B order), not bad data — deleting it silently would distort revenue/demand totals without anyone noticing. This project adds boolean outlier-flag columns so an analyst can choose to exclude them per-analysis without losing the underlying signal permanently.

**69. What's the difference between merge() and join() in pandas?**
`.merge()` is the general-purpose SQL-style join (inner/left/right/outer, on any column). `.join()` is a convenience method specifically for joining on the index. This project uses `.merge()` throughout since joins are typically on ID columns (`Product ID`, `Supplier`), not the DataFrame's index.

**70. Explain method chaining and why it's used.**
Calling multiple DataFrame methods in sequence (`df.groupby(...).agg(...).sort_values(...)`) without intermediate variable assignment — improves readability for linear transformation pipelines, though it can hurt debuggability if a step in the middle fails silently.

**71. What's the purpose of `np.random.default_rng(seed)` over the older `np.random.seed()`?**
The newer Generator API is the recommended, more robust random-number interface in NumPy — it avoids global state (each `Generator` instance is independent, safer for reproducibility across parallel code) unlike the legacy global `np.random.seed()`. This project seeds a single `Generator` once (`RANDOM_SEED = 42` in `config.py`) and threads it through every generation function so the entire dataset is exactly reproducible.

**72. How would you explain the "chronological simulation" approach for generating synthetic data?**
Instead of generating each row independently with random values, you process events (orders) in date order per entity (product+warehouse), maintaining running state (inventory level) that updates as you go — so values that must be internally consistent (inventory can't go negative, stock is only replenished when actually low) emerge naturally from the simulation instead of being faked after the fact.

**73. What's `np.select()` used for, and how is it different from nested `np.where()`?**
`np.select(condlist, choicelist, default)` evaluates multiple conditions and picks the corresponding value for each — cleaner and more readable than deeply nested `np.where()` calls once you have more than 2-3 conditions. This project uses it to map `Order Status` to `Delivery Status` across 5 possible states in one call.

**74. Why does `SUMX` (DAX) resemble `.apply()` or a list comprehension in pandas conceptually?**
Both express "iterate row-by-row, compute something using multiple columns from that row, then aggregate" — SUMX is DAX's row-context iterator, similar in spirit to `df.apply(lambda row: ..., axis=1)` in pandas, though pandas' vectorized alternative (`df['a'] * df['b']`) is almost always faster than `.apply()` and should be preferred when possible.

**75. What's a common pitfall when using `.astype(int)` on a boolean column?**
It's usually exactly what you want (`True`/`False` → `1`/`0`) — but if the column has NaN values first, `.astype(int)` will raise an error or produce unexpected results, since NaN can't cast cleanly to int. This project explicitly casts `is_delivered` and `stockout_flag` to int right before loading into SQLite, after confirming no nulls exist in those columns.

**76. What's the difference between `.mean()` and computing a weighted average in pandas?**
`.mean()` treats every row equally. A weighted average requires `(values * weights).sum() / weights.sum()` (or `np.average(values, weights=weights)`) when some rows should count more than others — e.g., average order value across categories should weight by order count, not just average the per-category averages equally.

**77. How would you detect and handle date-logic violations in a dataset (e.g., delivery before shipping)?**
Assert-style checks: `(df['Delivery Date'] < df['Ship Date']).sum()` should be 0; if not, investigate the generation/collection logic rather than silently filtering the bad rows. This project runs exactly this kind of check after both dataset generation and cleaning, and it caught two real, non-obvious bugs during development (see Q78, Q79).

**78. Walk me through a real bug you found and fixed in this project.**
The shipping-cost formula originally scaled with distance alone, ignoring product weight — so a lightweight ₹80 grocery item shipped 3,000km could rack up ₹30,000 in "freight," producing impossible negative profit margins. I traced it to the generator, rebuilt the cost model as weight × distance × mode rate (how real freight pricing actually works), added realistic per-category weight ranges, and excluded categories like Grocery from air freight entirely since it isn't commercially realistic.

**79. Describe a case where a KPI calculation had a subtle definitional bug.**
`Fill Rate` was originally computed as `Stock Issued / Demand`, but `Demand` included background inventory consumption accumulated since the *previous* order — unrelated to what this specific order requested — which artificially crushed the average fill rate to 13.7%. The fix was recognizing the correct denominator is `Order Quantity` (what was actually requested by this order), which brought the metric to a sensible, cross-checked 56.9%.

**80. Why validate a time-series model on a holdout period that includes your hardest test case (e.g., a seasonal peak) rather than a random or easy period?**
Because a model that only looks good on easy/average periods gives false confidence — the real business risk concentrates exactly at the peak (inventory planning, staffing). This project deliberately reports holdout accuracy on a window that includes the December peak, even though the number is worse than it would be on an average holdout, because that's the honest, decision-relevant number.

**81. What's `statsmodels.seasonal_decompose`, and what are its three output components?**
It splits a time series into Trend (long-term direction), Seasonal (repeating periodic pattern), and Residual (what's left over/noise) — additive or multiplicative. This project uses it to visualize weekly demand decomposition, confirming a clear trend and a strong Nov/Dec seasonal spike.

**82. Why might a library's built-in seasonal model (e.g., Holt-Winters) fail on a small dataset, and what's the alternative?**
Seasonal Holt-Winters typically needs at least 2 full seasonal cycles of *training* data to reliably initialize its seasonal component — with only 2 years total and a holdout carved out, there isn't enough left. The alternative used in this project: manually compute month-of-year seasonal indices from the available history and apply them to a separately-fit linear trend — simpler, fully transparent, and it validated successfully where the library's automatic method failed.

**83. What's MAPE, and what's a limitation of using it?**
Mean Absolute Percentage Error — average of `|actual - forecast| / actual` across all points, expressed as a percentage. It's intuitive but breaks down (divides by near-zero) when actual values are close to zero, and it penalizes under-forecasting and over-forecasting asymmetrically in percentage terms.

**84. How would you structure a data pipeline to be reproducible (like this one)?**
Seed all randomness explicitly, separate raw/generated data from processed/derived data (never overwrite raw), make each stage a standalone script with clear inputs/outputs, and assert data-quality invariants after each stage rather than assuming they hold. This project's `src/` folder follows exactly that pattern: `generate → clean_and_engineer → {inventory, logistics, forecasting} → load_to_sql`.

**85. What's the purpose of `pd.Grouper(key=..., freq=...)`?**
It lets you group a DataFrame by a time-based frequency (e.g., `'MS'` for month-start, `'W'` for weekly) directly inside a `.groupby()` call, without first setting the date column as the index. Used throughout this project's monthly/weekly trend analyses.

**86. What's the difference between `.apply()` and a vectorized NumPy operation, performance-wise?**
`.apply()` still executes a Python function once per row/group under the hood — much slower than true vectorization, which processes the whole array in compiled code. `.apply()` is sometimes necessary for genuinely row-dependent logic that has no vectorized equivalent, but should be a deliberate choice, not a default.

**87. Why use `.reset_index()` after a `.groupby()` operation?**
`.groupby()` results have the grouping column(s) as the index rather than a regular column, which can be inconvenient for merging, plotting, or exporting. `.reset_index()` turns that index back into regular columns.

**88. What's a practical difference between `np.nan` and `None` in a pandas DataFrame?**
In a numeric column, pandas typically converts `None` to `np.nan` automatically for consistency. In an object/string column, `None` and `np.nan` can coexist and behave slightly differently in comparisons — worth being explicit and checking `.isnull()` rather than `== np.nan` (which is always False due to how NaN comparisons work).

**89. What does `df.groupby(...).transform()` do, and when would you use it over `.agg()`?**
`.transform()` returns a result the same shape as the original DataFrame (broadcasting the group aggregate back to every row in that group), while `.agg()` collapses to one row per group. Useful when you need a group-level statistic (like a category average) available alongside the original row-level data for further calculation.

**90. How would you explain this whole project's Python architecture in 30 seconds?**
"One script generates a realistic, internally-consistent dataset via simulation rather than pure randomness. A second script cleans it and engineers features. Three parallel analysis scripts compute inventory, logistics, and forecasting metrics off that cleaned data. A final script loads everything into a proper SQL database. Every stage writes its output to disk and validates its own assumptions before the next stage runs."

---

## Supply Chain Analytics (20 Questions)

**91. What is EOQ (Economic Order Quantity), and what does it optimize?**
The order quantity that minimizes total inventory cost by balancing ordering cost (fixed cost per purchase order) against holding cost (cost of carrying inventory). Formula: `EOQ = √(2DS/H)` where D = annual demand, S = cost per order, H = annual holding cost per unit. This project computes it per-SKU using observed annual demand and a stated 20%-of-unit-cost holding cost assumption.

**92. What is safety stock, and what inputs does it depend on?**
Buffer inventory held above expected demand to protect against demand variability and supply lead-time variability, sized to hit a target service level. Formula used in this project: `Z × demand_std_dev × √(lead_time)`, where Z is the service-level z-score (1.65 for 95%).

**93. What is a reorder point, and how does it relate to safety stock?**
The inventory level at which a new purchase order should be triggered, calculated as `(average daily demand × lead time) + safety stock` — it's the point where remaining stock will just cover demand during the replenishment lead time, plus a buffer.

**94. Explain ABC inventory classification and its business purpose.**
Classifying SKUs by their contribution to revenue (or another value metric) into tiers — typically A (top ~70-80% of value from a small % of SKUs), B (next ~15-20%), C (the long tail). It focuses inventory-management effort (tighter forecasting, more frequent counts, higher service levels) where it has the most financial impact, rather than treating every SKU equally.

**95. What is fill rate, and how is it different from order fulfillment rate or perfect order rate?**
Fill rate measures the % of ordered quantity actually fulfilled from available stock. Order fulfillment rate is often used interchangeably but can also mean "% of orders fully shipped" (order-level, not unit-level). Perfect order rate is the strictest metric — an order counts only if it's delivered, on-time, AND not returned; all three conditions must hold.

**96. What causes a stockout, and what are the typical business responses?**
A stockout happens when demand exceeds available inventory — usually from underestimated demand variability, understated safety stock, or a supply-chain delay. Responses include increasing safety stock (cost tradeoff), improving demand forecasting, diversifying suppliers to reduce lead-time risk, or accepting backorders with clear customer communication.

**97. What is inventory turnover, and what does a high vs. low value indicate?**
Turnover = units sold / average inventory held, over a period — how many times inventory is fully cycled through. High turnover generally indicates efficient inventory use and fresh stock (typical for fast-moving categories like Grocery); low turnover can indicate overstocking, slow-moving SKUs, or obsolescence risk (more typical for categories like Furniture).

**98. What's the difference between a perfect order and an on-time delivery?**
On-time delivery only checks the timing condition. A perfect order additionally requires the order to have actually been delivered (not cancelled/backordered) and not returned — it's a stricter, more holistic measure of end-to-end fulfillment quality.

**99. How would you diagnose why a specific warehouse has poor delivery performance?**
Break the fulfillment cycle into its components — order-to-ship time (warehouse processing speed) vs. ship-to-delivery time (carrier/transit performance) — and compare each warehouse's split against the network average. In this project, that decomposition specifically isolated WH05's slow *processing* time (not carrier performance) as the root cause of its regional delivery lag.

**100. What's the tradeoff between transportation modes (e.g., Air vs. Sea)?**
Speed vs. cost, essentially. Air is fastest but most expensive per kg-km; Sea/Rail are slowest but cheapest. The right choice depends on the product's value density, urgency, and shelf life — this project found Air freight costs ~2.5x more (as % of revenue) than Sea/Rail, and correctly restricts low-value, regionally-distributed categories like Grocery from using it at all.

**101. What is demand forecasting bias, and why does it matter beyond just accuracy (MAPE)?**
Bias is the *direction* of forecast error (systematically over- or under-forecasting), separate from its magnitude. A forecast can have low MAPE but a concerning bias, or vice versa. Over-forecasting bias risks excess inventory/carrying cost; under-forecasting bias risks stockouts — the appropriate fix differs depending on which direction the bias runs.

**102. Why does demand forecast accuracy typically vary by product category?**
Categories differ in demand volatility (a smartphone's demand is driven by trends/promotions/launches; a grocery staple's demand is stable and habitual), and forecast difficulty scales with volatility. This project found a near-20-point forecast-accuracy gap between Grocery (90.6%) and Mobiles & Accessories (72.0%), consistent with that intuition.

**103. What is supplier lead time, and how does it affect inventory policy?**
The time between placing a purchase order and receiving the goods. Longer lead times require larger safety stock (since more can go wrong/demand can shift during that window) and push the reorder point earlier — it's directly embedded in both the safety stock and reorder point formulas.

**104. How would you evaluate supplier performance beyond just on-time delivery?**
Multiple dimensions: defect/quality rate, actual downstream return rate (does their documented quality metric match reality), lead time consistency (not just average, but variance), cost competitiveness, and responsiveness. This project cross-checked documented defect rate against actual observed return rate and found they correlate strongly — a good validation that the documented metric is trustworthy.

**105. What is warehouse capacity utilization, and what's the risk of both extremes?**
Current inventory units held as a percentage of a warehouse's stated capacity. Too high (over 100%) risks overflow, damaged goods, and operational inefficiency; too low wastes fixed facility costs and may indicate misallocated inventory. This project found an 8-point warehouse network with utilization ranging from 56% to 135% — a clear rebalancing opportunity in either direction.

**106. What's the difference between a backorder and a stockout?**
A stockout is the state of having zero available inventory for a demand event. A backorder is a specific order status/customer commitment made *despite* a stockout — the company promises future fulfillment once restocked, rather than cancelling the order outright.

**107. How does seasonality affect supply chain planning beyond just sales forecasting?**
It cascades into staffing (warehouse labor for peak processing volume), carrier capacity booking (freight gets more expensive and scarce during peak season), and safety stock timing (inventory needs to be pre-positioned *before* the demand spike, not reactively during it) — sales forecasting is the input, but the operational planning that follows is where seasonality actually costs or saves money.

**108. What's the business case for moving from a flat safety-stock policy to a per-SKU dynamic one?**
A flat policy (e.g., "30% of average demand" for every SKU) systematically under-protects high-volatility products and over-protects stable ones, wasting capital on the wrong SKUs. This project found the average demand coefficient of variation (2.9) far exceeds the flat 30% assumption baked into the original policy — direct evidence the flat approach is miscalibrated, not just theoretically suboptimal.

**109. How would you prioritize which supply chain problem to fix first, given limited resources?**
Look for findings confirmed by multiple independent metrics (higher confidence, less likely to be measurement noise), and estimate both the size of the financial/service impact and the implementation difficulty. This project's insights report explicitly ranks its "Top 5 Priorities" using exactly that logic — e.g., the reorder-point fix ranks #1 because it's confirmed three separate ways (Python model, raw data, SQL queries), not just because it sounds important.

**110. If you were extending this project for a real company, what would you build next?**
A live, refreshing data pipeline (not a static synthetic snapshot) connected to DirectQuery or a scheduled refresh, real supplier/carrier performance feeds instead of simulated ones, an A/B test framework to validate recommendations before full rollout (e.g., testing the Air-to-Road freight substitution on a subset of routes first), and RLS in Power BI so regional managers only see their own warehouse's data.
