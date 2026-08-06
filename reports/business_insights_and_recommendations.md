# Business Insights & Recommendations

Every insight below is drawn directly from the analytics built in Steps 3–7
(no hypotheticals) — cross-referenced against `data/processed/*.csv` and
`sql/03_business_queries.sql`. Each is paired with a specific recommended
action, not just an observation.

**Headline numbers**: ₹1,705.6 Cr revenue · ₹283.0 Cr profit (17.6% avg margin) · 100,000 orders · 92.3% on-time delivery · 56.9% fill rate

---

## Executive / Financial

1. **Total revenue is ₹1,705.6 Cr with ₹283.0 Cr profit (17.6% avg margin)** across 100,000 orders spanning 2024–2025. → Healthy top line, but the 6.3%–30.9% margin spread across categories (below) means the category mix has real room to shift toward profitability, not just volume.

2. **Grocery drives 28.4% of order volume but only 6.3% average margin and ~10% of total profit.** → Treat Grocery as a traffic/loyalty driver rather than a growth lever; don't measure its success by revenue share.

3. **Electronics and Mobiles & Accessories together generate the largest profit share** (₹692.0 Cr + ₹673.4 Cr) despite being only 17% of order volume. → Prioritize supply reliability investment here — a stockout on these SKUs costs the business the most per incident.

4. **South (₹4,138 Cr) and East (₹4,074 Cr) lead regional revenue; Central lags at ₹2,011 Cr** — roughly half the top regions. → Central also has the worst on-time delivery and warehouse execution (see Logistics #20 and Warehouse #15) — investigate whether weak service is suppressing regional demand rather than assuming lower demand is the root cause.

5. **Fashion (30.9%) and Beauty & Personal Care (27.8%) have the highest margins** but under 20% combined order share. → Strong case for expanding catalog depth and marketing spend in these two categories.

---

## Inventory

6. **ABC classification is a clean Pareto curve**: 79 products (20% of catalog) generate 69.9% of revenue (₹1,134 Cr); 230 products (57.5% of catalog) generate only 10.1% (₹163.5 Cr). → Apply tighter safety stock and more frequent replenishment to the 79 A-class SKUs; consider consolidating or delisting chronic C-class underperformers.

7. **Every one of the 400 products in the catalog is currently below its calculated reorder point.** → The existing replenishment policy is structurally undersized. Recommend a phased safety-stock increase, starting with A-class SKUs first.

8. **Average demand coefficient of variation is ~2.9**, far exceeding the flat 30%-of-mean assumption embedded in the current safety-stock policy. → Move to a per-SKU dynamic safety-stock formula scaled to each product's own observed volatility rather than one blanket rule (see `src/inventory_analytics.py` methodology).

9. **A-class products carry a far smaller average EOQ (42 units) than C-class products (387 units).** → Consistent with A-class SKUs' faster turnover. Validate purchase order cadence matches — over-ordering C-class SKUs in large batches ties up working capital in slow movers.

10. **Stockout rate varies dramatically by category**: Home & Furniture (83.7%) and Appliances (83.5%) vs. just 12.4% for Grocery. → Heavy/bulky categories are systematically under-stocked relative to their lumpy, bulk-order demand pattern. Increase safety stock specifically for these two categories first.

11. **Overall fill rate averages 56.9%** — on average, over four in ten ordered units aren't available for immediate fulfillment. → The single highest-leverage inventory KPI to improve; directly downstream of findings #7 and #8.

12. **Return rate averages 7.9% company-wide**, but is concentrated in specific suppliers rather than spread evenly (see Supplier section). → Quality-focused supplier reviews on high-value categories will have outsized financial impact per return avoided.

---

## Warehouse

13. **WH08 (Kolkata) runs at 135.3% capacity utilization while WH01/WH06 (Delhi NCR) sit at 56–57%.** → Rebalance regional inventory allocation from Kolkata toward the underutilized Delhi NCR facilities to reduce overflow and holding risk.

14. **Perfect Order Rate ranges from 75.7% (WH05, Nagpur) to 82.7% (WH08, Kolkata)** despite nearly identical order volumes (~11,800–12,000 each). → Since volume isn't the differentiator, this is a process/execution gap — benchmark WH05's operating procedures against WH08's.

15. **WH05 (Nagpur, Central region) has both the lowest Perfect Order Rate and the slowest average processing time (2.46 days vs. 0.66 days at WH08 — a 3.7x spread).** → WH05 is the common root cause behind two independent metrics (see also Logistics #20); prioritize it for a process audit.

16. **Average order-to-ship processing time ranges 0.66–2.46 days across the network.** → Standardize picking/packing SLAs; WH05's slow processing likely compounds its downstream delivery delay problem.

17. **Return rates cluster tightly (7.8%–8.6%) across all 8 warehouses.** → Returns are driven by product/supplier quality factors, not warehouse-specific handling — don't spend warehouse-ops budget chasing a returns problem that lives upstream.

18. **Grocery and Beauty & Personal Care correctly never ship via Air freight, with cross-region distances capped** — the warehouse network design already reflects real regional-distribution economics for fast-moving, low-value goods. → No change needed; use this as the positive baseline when auditing other categories' shipping-mode choices.

---

## Logistics

19. **Overall on-time delivery is 92.3%** across ~89,600 delivered orders. → Use as the company-wide target floor; flag any region/warehouse performing below it.

20. **Central region on-time delivery trails at 88.0% vs. 91.8–96.0% elsewhere.** → Traces directly to WH05 (Nagpur)'s slow processing time (Warehouse #15/#16) — fixing warehouse execution should directly lift this regional metric.

21. **Air freight costs 2.0% of revenue vs. 0.7–0.8% for Sea and Rail — a ~2.5x cost premium for speed.** → Audit which categories/orders default to Air vs. genuinely need it; shifting even 10% of non-urgent Air volume to Road/Rail could meaningfully cut logistics spend.

22. **DTDC carries the highest total logistics cost (₹3.92 Cr) of any carrier; Delhivery has the best on-time rate (92.7%).** → Consider rebalancing volume toward Delhivery for lead-time-sensitive shipments.

23. **Carrier on-time rates cluster tightly (92.1%–92.7%)** — carrier choice has far less impact on delivery performance than warehouse processing time or region. → Don't over-invest in carrier renegotiation; the bigger lever is internal warehouse execution (see Warehouse #16).

24. **The four costliest shipping-route combinations are all Air freight from the North region (₹7,300–8,200/shipment average).** → Prime candidates for a Road/Rail substitution pilot given the cost gap in #21.

25. **Shipping cost has the highest outlier rate of any cost field (11% of orders flagged via IQR)**, well above Procurement (1.3%) or Selling Price (1.5%). → Shipping is the most volatile cost line item and deserves its own dedicated cost-control initiative, separate from procurement or warehousing.

---

## Demand Forecasting

26. **Forecast accuracy ranges from 90.6% (Grocery) to 72.0% (Mobiles & Accessories)** — an 18.6-point spread. → Apply category-specific forecasting cadence; fast-moving tech categories need shorter-horizon, more frequently refreshed forecasts than staple goods.

27. **Appliances shows the largest over-forecasting bias (+1.74 units avg); Beauty & Personal Care shows the largest under-forecasting bias (−0.41).** → Appliances' over-forecasting risks excess carrying cost; Beauty's under-forecasting risks stockouts. Both need explicit bias-correction terms in the next model iteration.

28. **A trend-only forecasting baseline failed badly (~100% MAPE) specifically on the Nov/Dec holiday window; an explicit seasonal-index model cut that to 17.9% MAPE on the same holdout.** → Seasonality isn't a minor refinement here — it's the single largest source of forecast error in this business, and any production model must account for it explicitly.

29. **Revenue jumps roughly 60% in November vs. October, consistently across both years in the dataset.** → This is a repeatable structural pattern, not noise. Inventory and staffing plans should build the Nov/Dec surge in as a standing assumption.

30. **Weekend order volume (28,330 orders) is about 40% of weekday volume, with nearly identical average order value** (₹169,809 vs. ₹170,863). → Demand character doesn't meaningfully shift on weekends — a useful negative finding that means no special weekend-specific inventory or staffing strategy is required, saving planning effort for higher-impact areas.

---

## Supplier Performance

31. **Supplier SUP019 (Patla-Gaba) has the highest actual return rate (10.0%) despite a short 3-day lead time.** → Fast delivery isn't compensating for quality issues; flag for a quality audit independent of lead-time performance.

32. **The five suppliers with the lowest return rates (5.6%–6.6%) all also have the lowest documented defect rates (0.01).** → Defect rate is a strong leading indicator of actual downstream returns — promote it to a primary metric on the supplier scorecard.

33. **Supplier lead times range 3–21 days with no clear correlation to return/defect rates.** → Lead time and quality are independent levers; negotiate them separately rather than assuming faster suppliers are lower quality (or vice versa).

34. **The five best-performing suppliers by return rate collectively supply ~21,700 orders** — a meaningful share of total volume. → Real opportunity to shift additional A-class product volume toward this proven cohort.

---

## Summary: Top 5 Priorities

Ranked by estimated business impact and how many independent metrics each one touches:

| Priority | Insight | Why it's top-ranked |
|---|---|---|
| 1 | Fix the reorder point / safety stock policy (#7, #8, #11) | Confirmed three independent ways (Python EOQ model, raw stockout flag, SQL queries); highest-leverage single fix |
| 2 | Audit and rebalance WH05 (Nagpur) operations (#14, #15, #16, #20) | Root cause behind both the worst warehouse Perfect Order Rate and the worst regional on-time delivery |
| 3 | Rebalance WH08 (Kolkata) capacity (#13) | 135% utilization is an operational risk, not just an efficiency gap |
| 4 | Build seasonality into the forecasting model (#28, #29) | Single largest source of forecast error identified in the whole analysis |
| 5 | Audit Air freight usage for non-urgent shipments (#21, #24) | Clear, quantified cost-reduction opportunity with no service-quality tradeoff for regionally-distributed categories |
