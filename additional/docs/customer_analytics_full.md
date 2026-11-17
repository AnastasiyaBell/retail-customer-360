# Customer analytics methodology

> Supplementary material preserved from the broader project. Original scope/output-path descriptions below are historical context. Use the main README for the focused business boundary and additional/README.md for current notebook locations.

## Paid-basket history and cutoff

Use positive quantity and positive retailer-sales lines, validated at cent precision as in notebook 02. Aggregate to household/basket/source-day. Build features from rows with day <= cutoff; never read future rows in the feature SQL. Recency uses last observed paid purchase over available history. Frequency/monetary use `(cutoff-180, cutoff]`; 30/60/90-day features use the same open-left/closed-right convention.

The feature population consists of households with at least one paid basket by cutoff. For prediction, require recency < 180, equivalent to a paid basket in the last 180 days. Newly observed history is not acquisition tenure. Households with no recent paid purchases remain in the descriptive RFM snapshot but have no model risk score outside the modelling population.

## RFM scoring and rules

Active households receive percentile-based R/F/M scores from 1 to 5: lower recency is better, higher frequency and sales are better. Use average ranks for ties and ceil(percentile * 5). Equal values receive equal scores; bins need not be equal-sized. Inactive households receive F=1, M=1 and the hibernating label.

Rules in precedence order:

1. Observed purchase history <= 30 days: Newly observed.
2. R>=4 and F>=4 and M>=4: Champions.
3. R>=3 and F>=4: Loyal.
4. Recency>30 and F>=3: At risk.
5. Recency>90: Hibernating.
6. R>=4 and F<=2: Potential loyalists.
7. Otherwise: Occasional.

Finally force Hibernating when frequency_180=0. These are proposed CRM rules, not validated causal or churn classes. Zero households in a segment is a valid dataset result, not a reason to invent members.

## Retention and cohorts

Use fixed 30-source-day periods starting at source day 1, not calendar months. First observed paid purchase determines cohort; this is not acquisition. Cohort retention at age t equals distinct cohort households purchasing in that period / original cohort size. T0 is structurally 100% for complete cohorts. The curve can rise through reactivation.

Only periods whose end day is <= observation cutoff have a reported rate. Partial periods retain observation_complete=False and a blank rate; future cells are absent. Previous-period retention is the intersection of buyers in consecutive complete periods divided by buyers in the previous period. Different denominators mean this is not the same as cohort retention or full-history repeat purchasing. Small cohorts and the frequently-shopping source panel limit generalisation.

## K-Means

Fit on active households' log1p(recency, frequency_180, monetary_180), scaled to unit variance. Compare K=2..6 by silhouette with a fixed random seed; fit the chosen K using another seed and report adjusted Rand stability. Profile clusters using original-scale medians. IDs are arbitrary, and inactive households receive cluster=-1. K-Means is supplementary to interpretable RFM, not a supervised segmentation performance claim.

## CLV-style scenario boundary

Actual lifetime, margin, acquisition cost and causal survival are not observed. Therefore do not claim an estimated true CLV. The implemented value is discounted six-month contribution under assumptions:

`monthly_sales_run_rate = eligible_sales_last_180_days / 6`

`scenario_value = SUM(monthly_sales_run_rate * assumed_margin * assumed_survival^m / (1+monthly_discount_rate)^m), m=1..months`

`monthly_discount_rate = (1+annual_discount_rate)^(1/12)-1`.

Defaults: six months, margin 25%, survival 90% per month, annual discount 10%. These are declared planning assumptions. The run-rate can be misleading for new, seasonal or inactive customers. Purchase retention is not silently used as contractual customer survival. Sensitivity to 80/90/100% survival is shown in notebook 04.
