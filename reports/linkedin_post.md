# LinkedIn Post

🚀 Just wrapped up a project I'm genuinely proud of: an end-to-end Supply Chain Analytics platform, built the way I'd want to see it done at a real company — not a tutorial copy-paste.

The stack: Python → SQL → Power BI, covering 100,000 orders across 400 products, 8 warehouses, and 25 suppliers, modeled on a real Indian e-commerce operation.

A few things I'm most proud of:

📊 Built a chronological inventory simulation (not random sampling) so that stock levels, delivery delays, and costs are all internally consistent — the kind of detail that matters when someone actually opens your data.

🔍 Caught two real bugs during validation — a shipping-cost model that ignored product weight, and a Fill Rate calculation with the wrong denominator — and fixed both at the root cause instead of patching symptoms. Documenting that process, I think, is more valuable than pretending the data was perfect from the start.

📦 Cross-validated a major finding — that the entire product catalog sits below its calculated reorder point — three independent ways: a from-scratch EOQ/safety-stock model in Python, raw stockout flags, and SQL window-function queries. All three agree.

📈 A textbook seasonal forecasting model failed badly (~100% error) on the holiday peak specifically because of limited historical data — so I built a transparent, explainable seasonal-index model instead, which held up to 82% accuracy on the same test.

The result: 34 concrete, numbers-backed business recommendations — not "optimize your supply chain," but specific findings like "Warehouse WH05 is the root cause behind both the worst Perfect Order Rate and the region's delivery delays."

Full project (code, SQL, Power BI spec, and the full insights report) on GitHub: [link]

#DataAnalytics #SupplyChainAnalytics #PowerBI #SQL #Python #PortfolioProject
