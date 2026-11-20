# Reproduce the focused analysis

Use Python 3.12. For a new clone/environment:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-lock.txt
.venv/Scripts/python.exe -m ipykernel install --prefix .venv --name retail-customer-360 --display-name "Python (retail-customer-360)"
```

Keep an existing working .venv rather than recreating it unnecessarily. Place original unpacked CSVs in data/raw; see README for the source link. All raw/derived files remain Git-ignored.

## Main reading order

Run notebooks 01_data_understanding, 02_customer_metrics, 03_categories_and_discounts, 04_rfm_segments, 05_no_purchase_prediction, 06_crm_campaign_scenarios, and 07_weekly_sales_forecast. Select the project .venv/Scripts/python.exe interpreter and Run All. Each reconstructs its own needed state; notebook 06 first needs the canonical pipeline outputs.

Notebook 01 inventories all eight sources, including causal_data. Notebook 03 needs only transactions and products. RFM notebook 04 contains only interpretable segments. Notebook 05 is a historical purchase-risk forecast, not a coupon response model. Notebook 06 selects one hypothetical offer, not COUPON_UPC recommendations. Notebook 07 reads only the raw transaction file, executes its own rolling forecast evaluation, and writes its figure to reports/figures. It forecasts as of the end of complete source week 101; week 102 is partially observed and excluded.

## Refresh the existing technical outputs

```powershell
.venv/Scripts/python.exe scripts/run_pipeline.py
```

This existing command still refreshes **both main and supplementary** analytics, models and BI tables to preserve the export contract. The reorganisation changes the reading path, not the numerical algorithms or pipeline scope. It does not rerender notebook outputs or rewrite narrative reports. Configuration and source hashes are saved locally. See automation.md for period support and failure/rerun behaviour.

## Optional notebooks

- additional/notebooks/01_promotional_placements.ipynb: causal_data matching, duplicate keys and display/mailer composition. Requires transactions, products and causal_data.
- additional/notebooks/02_retention_clustering_and_value.ipynb: cohorts, retention, K-Means and contribution scenarios. Independent setup rebuilds RFM features.

Run from their actual nested folders with the same project interpreter. Root discovery searches parent directories; supplementary plots save to additional/figures. Derived data still writes under ignored data/processed. See [additional index](../additional/README.md).

## Verification

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

The monetary/receipt, time-leakage, censored-retention and budget checks remain available, including tests for supplementary code. Focused [Power BI](../powerbi/dashboard_plan.md) and [Tableau](../tableau/dashboard_plan.md) plans are manual handoffs; no workbook is published automatically.

## Reading the code

Code now uses an 88-character line limit and short step-by-step cells, with intermediate table previews. See [readability conventions](code_readability.md). Run cells in order so later steps can reuse the earlier variables.
