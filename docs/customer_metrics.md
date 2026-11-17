# Customer metrics methodology

Implemented in [SQL](../sql/customer_metrics.sql), the [summary query](../sql/customer_metrics_summary.sql), the [Python runner](../src/retail_customer_360/metrics.py), and the [executed notebook](../notebooks/02_customer_metrics.ipynb).

## Scope and population

The window includes both start and cutoff days. The default covers all observed days (currently 1 to 711). The population contains every household observed on or before the cutoff, including previously observed households with no paid basket in the selected window. Future-only identifiers are not included. Demographics are not required.

## Eligibility and money

A paid line has `QUANTITY > 0 AND SALES_VALUE > 0`. A paid basket has at least one such line. Sum only eligible lines within those baskets. This excludes free-only receipts and zero-quantity amounts; it does not classify them as erroneous. Raw sources are unchanged. Reconciliation explicitly reports excluded rows and sales.

`SALES_VALUE` is retailer proceeds under the source definition, not necessarily customer payment or profit. No discounts are deducted a second time. Monetary strings are converted directly to `DECIMAL(18,2)` after validation. There are 29 scientific-notation near-zero amounts in the source; values with absolute magnitude below 1e-9 USD and zero quantity are explicitly permitted and become zero cents. Their original text is retained in the temporary `monetary_normalization` diagnostic table. Other non-cent formats fail validation. This policy is specific to observed negligible residues, not blanket rounding of arbitrary input.

## Metrics

| Column / metric | Definition |
|---|---|
| `purchase_baskets` | Count of eligible receipts in the window, not product rows |
| `purchase_days` | Distinct source days containing eligible receipts |
| `eligible_sales_value` | Eligible retailer proceeds, USD |
| `average_basket_value` | Eligible sales / paid baskets; NULL if no paid basket |
| `first_purchase_day_in_window` | First eligible purchase day within this window; not acquisition |
| `last_purchase_day_in_window` | Last eligible purchase day within this window |
| `recency_days` | Cutoff minus last eligible day within the window; NULL if none |
| `baskets_per_30_window_days` | Basket count x 30 / inclusive window length; not tenure-adjusted |
| `repeat_buyer` | At least two paid baskets; same-day receipts can qualify |
| `multi_day_buyer` | Paid baskets on at least two source days |
| `mean_days_between_baskets` | Mean consecutive-basket day gap per household within the window |
| `median_days_between_baskets` | Median such gap per household; NULL when fewer than two baskets |

Overall AOV uses summed sales divided by summed baskets. Repeat-buyer percentages use purchasing households as denominator; the full observed population is reported separately. Frequency is reported both per purchasing household and per observed household. Pooled gap statistics weight intervals, not household averages. Same-day gaps are zero; the first eligible basket in a window has no measured prior gap.

## Limits

The source households were frequent shoppers; full-history repeat rates do not estimate general-population or short-term retention. Window boundaries censor histories. Quantity units, excluded source anomalies and alternate eligibility policies require further work. The default all-history mart is descriptive and must be rebuilt at historical cutoffs before use as model features. No margin, campaign uplift, retention, or CLV is estimated here.

## Local outputs

`data/processed/customer_metrics.parquet`, `customer_metrics.csv`, `basket_metrics.parquet`, and `customer_metrics_summary.json` are regenerated snapshots for the most recent run. The entire data directory is Git-ignored. Changing window parameters overwrites these local snapshots.
