# Data inventory and modelling decisions

The original CSVs are preserved in `data/raw/`. See `reports/data_quality.md` for measured counts and `reports/data_quality.json` for inferred types and per-column missingness.

## Source grains to validate

| File | Intended interpretation | Candidate keys / relationships |
|---|---|---|
| transaction_data | Basket product line observations | Household, basket, product, source day; do not assume one row per basket-product |
| product | Product attributes | PRODUCT_ID |
| hh_demographic | Partial household demographic coverage | household_key |
| campaign_desc | Campaign descriptions and relative day intervals | CAMPAIGN |
| campaign_table | Household campaign assignments | household_key + CAMPAIGN |
| coupon | Coupon-to-product eligibility mapping | COUPON_UPC + PRODUCT_ID + CAMPAIGN |
| coupon_redempt | Observed household coupon redemptions | Validate repeated household/day/coupon/campaign combinations |
| causal_data | Product/store/week promotional exposure records | Validate PRODUCT_ID + STORE_ID + WEEK_NO and exposure categories |

Candidate keys are hypotheses until checked. The initial audit does not validate every candidate key.

## Initial decisions

- Build a household dimension from transaction identifiers, then left join demographics. Missing demographic records must not remove customers.
- Keep source day numbers until calendar date semantics are verified.
- Basket frequency counts distinct baskets, not product rows.
- Flag and investigate zero-value / non-positive-quantity records and apparent duplicates; do not delete them automatically.
- Keep each discount column separate. Confirm the definition of SALES_VALUE before defining revenue, gross sales, or discount rates.
- Customer acquisition dates are unavailable unless explicitly documented. Use first observed purchase for descriptive cohorts and disclose left censoring.
- Campaign assignment is an observed historical marketing decision, not proof of random assignment.

## Next checks

Validate discount semantics against the original user guide; inspect anomaly examples; validate coupon and promotion grains; establish analytical eligibility and an explicit observation cutoff before creating the customer mart.
