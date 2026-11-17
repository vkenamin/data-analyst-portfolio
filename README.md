# Data Analyst Portfolio — Viken Amin

Three end-to-end projects on real data. Each one starts from a business question, checks the data before
trusting it, and ends with numbers a manager can act on.

| # | Project | Business question | Tools |
|---|---|---|---|
| 1 | [**E-commerce Sales & Customer Analytics**](01-ecommerce-sql-powerbi/) | Where does revenue come from, what hurts satisfaction, which customers matter? | PostgreSQL, SQL, Power BI, DAX, Python |
| 2 | [**Retail Demand Forecasting & Inventory Planning**](02-retail-demand-forecasting/) | How much will each product sell, how much safety stock is needed, what do empty shelves cost? | Python, pandas, statsmodels, Jupyter |
| 3 | [**Marketing A/B Test**](03-ab-test-excel-stats/) | Did the ad campaign really work, and should it roll out? | Excel, statistics, Python, Tableau |

## Headline results

- **Project 1** — 96K orders, R$13.2M revenue: orders arriving 8+ days late average **1.7★** vs 4.3★ on time;
  only **3%** of customers ever reorder; top 20% of customers bring **57%** of revenue.
- **Project 2** — 1,437 Walmart food products: department forecast within **6% WAPE**; SNAP days lift sales **11%**
  (p < 0.001); **867 likely stockouts ≈ $115K** lost revenue, 85% on A-items.
- **Project 3** — 588K users: ads lift conversion **+43%** (p < 0.001, ≈ 4,300 extra conversions), but only for users
  who see **25+ ads**.

## Skills covered

| Skill | Where |
|---|---|
| SQL — joins, CTEs, window functions, cohorts, segmentation | Project 1 |
| Relational database design (PostgreSQL, keys, indexes, views) | Project 1 |
| Data cleaning & data-quality validation | All three |
| Excel — COUNTIFS, named ranges, statistical functions, charts, dashboard | Project 3 |
| BI dashboards — Power BI (star schema, DAX), Tableau | Projects 1, 3 |
| Python — pandas, NumPy, matplotlib, Jupyter | All three |
| Statistics — hypothesis tests, confidence intervals, power analysis | Projects 2, 3 |
| Forecasting & inventory analytics | Project 2 |
| KPI design & business recommendations | All three |
| Reproducible work — scripts, verification, Git | All three |

## Data sources
All public: [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) ·
[M5 Forecasting (Walmart)](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data) ·
[Marketing A/B Testing](https://www.kaggle.com/datasets/faviovaz/marketing-ab-testing).
Raw files aren't committed (size); each project's README says where to put them.
