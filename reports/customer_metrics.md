# Customer metrics - initial descriptive snapshot

Computed by [02_customer_metrics.ipynb](../notebooks/02_customer_metrics.ipynb), using the [shared SQL mart](../sql/customer_metrics.sql). This is a saved summary of the full-window run; rerun code to refresh results after changing data or parameters.

| Metric | Result |
|---|---:|
| Inclusive source-day window | 1 to 711 |
| Observed households | 2,500 |
| Households with paid baskets | 2,500 |
| Paid baskets | 275,539 |
| Eligible retailer sales, USD | 8,057,443.80 |
| Average eligible basket value, USD | 29.24 |
| Baskets per purchasing household in window | 110.2156 |
| Repeat buyers (at least two baskets) | 2,497 |
| Repeat buyers / purchasing households | 99.88% |
| Buyers purchasing on at least two days | 2,497 |
| Pooled mean interpurchase gap, days | 5.6697 |
| Pooled median interpurchase gap, days | 2.00 |

## Interpretation

Eligible lines have positive quantity and positive sales. Basket sales and AOV use those lines only; they are not a verified complete-receipt payment amount. These are retailer proceeds, not profit. Repeat percentages describe the entire 711-day window among purchasing households, not 30-day retention or campaign effectiveness. Same-day receipts count as separate purchases; multi-day purchasing is reported separately.

The notebook shows the complete raw-to-eligible reconciliation and the 29 negligible monetary residues rounded to zero cents on zero-quantity rows. All raw files remain unchanged. Household-level exports are local and excluded from Git. See [methodology](../docs/customer_metrics.md) for exact definitions, caveats and rerun behaviour.
