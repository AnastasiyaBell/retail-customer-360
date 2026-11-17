# Additional customer analytics

Supporting exploration retained outside the main coupon-focused reading path. Files are moved and split, not discarded. No raw data or household dataset has been moved into this folder.

## Independent notebooks

1. [Promotional placements](notebooks/01_promotional_placements.ipynb): product-store-week key checks, display/mailer sales composition and coverage. Requires causal_data.csv in addition to transactions/products.
2. [Retention, clustering and value](notebooks/02_retention_clustering_and_value.ipynb): first-observed cohorts, repeat-period retention, exploratory K-Means and assumption-based contribution-value scenarios. Rebuilds its own RFM feature setup; no earlier notebook execution required.

3. [Coupon recommendation experiment](notebooks/03_coupon_recommendation_experiment.ipynb): independent historical TypeB/TypeC candidate ranking, popularity comparison, future-product and redemption diagnostics, explicit limitations and a prospective test plan. The main USD 2 scenario remains unchanged.

4. [Coupon recommendations in Pandas](notebooks/04_coupon_recommendation_pandas.ipynb): the same experiment implemented with Pandas, executed and checked against SQL. [Runtime and memory comparison](reports/coupon_pandas_benchmark.md).

Run with the project .venv interpreter. Repository root discovery works from these nested folders. Supplementary figures are saved in [figures/](figures/), while derived data remains Git-ignored under data/processed.

## Methodology and earlier broad reports

- [Full customer analytics methodology](docs/customer_analytics_full.md)
- [Full category/discount/placement methodology](docs/sales_promotions_eda_full.md)
- [Full six-stage results snapshot](reports/full_project_results.md)
- [Earlier full visual report](reports/full_visual_findings.md)

The broad results snapshot records the original technical scope; it predates the optional household-coupon relevance prototype and does not describe its results. The main README and focused report define the current business boundary.

## Extended dashboard plans

- [Full Power BI plan](dashboard_plans/powerbi_full_plan.md)
- [Full Tableau plan](dashboard_plans/tableau_full_plan.md)

Retention, K-Means and scenario-value pages are optional additions. Current technical refresh still exports these supporting tables for compatibility; the primary reading path and focused dashboard plans do not require them.
