# Sales and promotions EDA methodology

> Supplementary material preserved from the broader project. Original scope/output-path descriptions below are historical context. Use the main README for the focused business boundary and additional/README.md for current notebook locations.

## Scope

Notebook 03 uses the same inclusive source-day window and paid-line rule as notebook 02. It reads transaction, product and promotion CSVs without changing them. Shared preparation lives in `src/retail_customer_360/promotions.py` and `sql/sales_promotions_eda.sql`. SQL prepares aggregates; Pandas and Matplotlib create charts. This is exploratory association analysis, not an uplift model.

## Categories

Join unique product identifiers to transaction lines. Map whitespace-only or explicit unspecified commodity descriptions to an unknown category, and preserve unmatched products separately. Rank `COMMODITY_DESC` categories by eligible retailer sales. Household reach is distinct purchasing households per category / all households observed by the cutoff. Reach overlaps across categories. Source labels such as `COUPON/MISC ITEMS` are not automatically recoded into a product class.

## Discounts

A basket has a reduction type when any eligible line has a negative corresponding adjustment. Loyalty, manufacturer-coupon and retailer-match flags overlap. Positive adjustments are exceptions shown separately, never folded into reductions using absolute values. Sum the magnitudes of negative adjustments only, keeping funding types separate. Do not deduct these amounts again from `SALES_VALUE` or describe them as incremental profit. Amounts are validated at cent precision; discount percentages against a reconstructed list price are not estimated.

## Promotion matching

Match on product, store and original source week. Validate required transaction keys and consistent store/week per basket. Aggregate matching promotion rows to one record per needed key. Use codes only for keys with exactly one source record; duplicated keys are ambiguous even if codes agree. Preserve unmatched records, missing codes and explicit `0` codes as separate categories. Confirm exact line and sales totals before and after joining.

The uniqueness audit is restricted to keys needed by eligible purchases, not a global audit of the complete promotion file. Charts include only purchased-product observations; zero-purchase product-store-week combinations are absent. Compare composition shares, not causal lift. Assortment, prices, stores, targeting, time and incomplete exposure coverage can confound differences. An absent promotion row does not establish absence of promotion or household ad exposure.

## Time and distributions

Notebook 02 validates observed day-to-week mapping and uses original source weeks, without assigning calendar dates. Weeks with fewer than seven observed transaction days are marked, not assumed to reflect a fall in demand. Household frequency charts retain zeros and the full range. Gap histograms retain zero-day intervals and the full tail, using labelled unequal bins on a symlog axis. Concentration curves rank descending household spend; top groups round up to whole households.

## Outputs and checks

Eight PNGs are saved under `reports/figures/`; the aggregate report is `reports/visual_findings.md`. Notebook 03 saves eight local plotting tables under Git-ignored `data/processed/eda/`. Snapshot exports are overwritten when rerunning with other parameters. Assertions reconcile categories, placement partitions, eligible lines and paid baskets. Unit tests cover duplicate/missing placement keys and discount-sign interpretation.
