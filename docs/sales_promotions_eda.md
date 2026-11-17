# Main EDA: categories and discounts

[Notebook 03](../notebooks/03_categories_and_discounts.ipynb) uses transaction_data.csv and product.csv with the same paid-line rule and observation window as notebook 02. No causal_data read or placement join is needed.

Unique product keys protect sales totals when joining categories. Blank/unspecified commodity descriptions become an explicit unknown category; unmatched products remain separate. Category reach counts distinct households buying a category divided by the entire observed household population. Reach overlaps across categories. Mixed source classifications such as COUPON/MISC ITEMS need investigation before merchandising conclusions.

A negative signed adjustment indicates a reduction. Loyalty, manufacturer-coupon and matching flags can overlap within a basket. Positive adjustments remain exceptions and are not turned into reductions with ABS. Funding types are separate, and amounts are not deducted from SALES_VALUE again. Only eligible paid lines are covered.

The main notebook saves three figures under reports/figures and four local aggregate CSVs under ignored data/processed/eda. These are aggregate category descriptions, not household-category preferences or coupon recommendations.

[Additional placement analysis](../additional/notebooks/01_promotional_placements.ipynb) and the [full methodology](../additional/docs/sales_promotions_eda_full.md) preserve display/mailer joins and coverage caveats. Supplementary charts are in additional/figures.
