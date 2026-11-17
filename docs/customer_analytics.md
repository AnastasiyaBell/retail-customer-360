# Main customer analytics: RFM

The main [RFM notebook](../notebooks/04_rfm_segments.ipynb) describes households using eligible paid baskets as of a cutoff. Recency is time since the latest observed paid purchase; frequency and monetary use the last 180 days. Observed history is not verified acquisition tenure.

Scores range 1 to 5. Lower recency and higher frequency/monetary receive higher scores. Equal values share average percentile ranks; groups need not be equal-sized. Proposed labels, in precedence order: newly observed history <=30 days; Champions (R/F/M >=4); Loyal (R>=3,F>=4); At risk (recency>30,F>=3); Hibernating (recency>90); Potential loyalists (R>=4,F<=2); otherwise Occasional. No paid activity in the last 180 days forces Hibernating.

These labels are initial analyst rules, not verified churn classes or coupon-response estimates. They are not inputs to the current predictive model or scenario ranking; they provide explanation and reporting context. RFM alone cannot choose a specific coupon.

The [full methodology](../additional/docs/customer_analytics_full.md) and [additional notebook](../additional/notebooks/02_retention_clustering_and_value.ipynb) retain cohorts, retention, K-Means and the contribution-value scenario. No formula was changed during this reorganisation.
