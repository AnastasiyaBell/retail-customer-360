# Initial audit findings

- 2,595,732 transaction rows, 276,484 baskets, and 2,500 purchasing households.
- Transactions cover source days 1 through 711. Calendar dates have not been assigned.
- No exact full-row transaction duplicates found.
- No duplicate product, demographic household, campaign description, or household/campaign assignment keys found in the initial checks.
- Each basket is associated with one household, source day, and store.
- All transaction product identifiers match the product table.
- Demographics cover 801 of 2,500 purchasing households (32.04%). Preserve the other households through left joins.
- There are 14,466 zero-quantity rows and 18,850 zero-sales-value rows. These counts can overlap. Negative quantities and negative sales values were not found. Do not assume this proves returns are absent.
- There are 36 rows with at least one positive discount field. Inspect these and verify source sign conventions before applying discount formulas.
- Product attributes contain whitespace-only entries: 15 each in department, commodity, and subcommodity; 30,607 in product size. SQL NULL checks alone would miss these.
- The campaign file extends to source day 719, beyond the last observed transaction day 711. Campaign outcomes near the end of observation are incomplete.
- No SQL NULL values were detected by the initial CSV parsing. This does not establish that there are no undocumented missing-value codes.

## Next analytical milestone

Confirm source field definitions, inspect anomalous transaction examples, and choose explicit purchase eligibility rules. Build a customer mart from all observed household identifiers without requiring demographic coverage. Keep source totals available for reconciliation.

Predictive labels must have a complete follow-up window: with the current transaction coverage, a cutoff later than source day 681 cannot support a full observed 30-day outcome window.
