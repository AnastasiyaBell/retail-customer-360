# Source data dictionary

Prepared on 2026-11-01 for the eight raw CSV files in this repository. This dictionary explains source fields; it does not rename columns or change data.

## Evidence and conventions

- **Documented meaning:** paraphrased from the original *The Complete Journey User Guide* and the package-maintainer references linked beside each table.
- **Observed locally:** headers, inferred DuckDB types, row counts and audit findings from [data_quality.json](../reports/data_quality.json); selected categorical values were also read directly from the CSVs while preparing this dictionary. Counts are a snapshot, not enforced constraints.
- **Proposed / pending:** modelling choices, unvalidated candidate keys, calendar mapping, and unresolved source semantics are labelled explicitly.
- Identifiers are nominal codes even where DuckDB infers `BIGINT`. Do not average them. Barcode-like identifiers may be stored as text in staging to protect formatting. Monetary fields are currently inferred as `DOUBLE`; consider an explicitly validated fixed-point type for financial transformations.
- The R package contains a processed, shorter version of the data, with renamed fields, changed time representations and different row counts. Its dates, positive-discount examples, and numerical ranges are not definitions of our raw release.
- Types below are inferred physical types, not business data types or a final production schema.

## Tables and columns

### `transaction_data.csv`

**Rows in saved audit:** 2,595,732. **Grain:** One source receipt-line observation; no single row key is assumed.

Definitions: [transaction reference](https://bradleyboehmke.github.io/completejourney/reference/transactions.html) and [original guide, p. 4](https://manuals.plus/m/ad83946d9648be9e5080c33c4fd2a9b66aace5bbeb875808d390c3f1df872741). Raw field names are retained below.

| Column | Inferred type | Meaning | Units / representation | Interpretation and joins |
|---|---|---|---|---|
| `household_key` | `BIGINT` | Household identifier; the customer entity in this project. | Identifier | Repeats across receipts; join to a household dimension built from transactions, not only demographics. |
| `BASKET_ID` | `BIGINT` | Identifier of a shopping receipt / purchase occasion. | Identifier | Repeats across product lines. Count distinct values for observed baskets. |
| `DAY` | `BIGINT` | Relative day on which the purchase was recorded. | Source day index | Observed transaction coverage is 1?711. A verified calendar origin is not yet established. |
| `PRODUCT_ID` | `BIGINT` | Identifier of the product on this receipt line. | Identifier | Join to product.PRODUCT_ID; basket plus product is not assumed to identify a unique row. |
| `QUANTITY` | `BIGINT` | Recorded product quantity for the line. | Source quantity units | Do not assume quantities are comparable physical units across products. Zero values and extremes require investigation; never divide by zero. |
| `SALES_VALUE` | `DOUBLE` | Dollar proceeds recorded for the retailer for this line. | USD per line | Already reflects retailer loyalty and coupon-matching adjustments; manufacturer reimbursement can make this different from customer payment. Not unit price or profit. |
| `STORE_ID` | `BIGINT` | Identifier of the store recording the purchase. | Identifier | Use with product and source week for promotion matching; there is no separate store master among the eight files. |
| `RETAIL_DISC` | `DOUBLE` | Signed adjustment associated with the retailer loyalty programme. | USD per line | Usually negative in these CSVs, with positive exceptions. Preserve signs; do not subtract discounts again from SALES_VALUE. |
| `TRANS_TIME` | `VARCHAR` | Source transaction clock-time field. | Text; working interpretation HHMM | For example, 1631 is interpreted as 16:31. Keep leading zeroes; validate hours/minutes before parsing. Time zone is not documented in the checked sources. |
| `WEEK_NO` | `BIGINT` | Source week identifier for the purchase. | Source week index | Observed transaction range is 1?102. Not an ISO week number; do not import the R package?s 1?53 range or invent a DAY-to-week rule. |
| `COUPON_DISC` | `DOUBLE` | Signed manufacturer-coupon adjustment recorded on the line. | USD per line | Manufacturer funding differs from a retailer-funded markdown. Do not equate it with retailer marketing cost. |
| `COUPON_MATCH_DISC` | `DOUBLE` | Signed extra reduction from the retailer matching a manufacturer coupon. | USD per line | A separate retailer adjustment; retain separately from COUPON_DISC. |

### `product.csv`

**Rows in saved audit:** 92,353. **Grain:** One product record; PRODUCT_ID uniqueness checked.

Definitions: [product reference](https://bradleyboehmke.github.io/completejourney/reference/products.html). Raw field names are retained below.

| Column | Inferred type | Meaning | Units / representation | Interpretation and joins |
|---|---|---|---|---|
| `PRODUCT_ID` | `BIGINT` | Product identifier. | Identifier | Unique in the initial audit; reference key for transaction and coupon product identifiers. |
| `MANUFACTURER` | `BIGINT` | Manufacturer identifier. | Identifier | A code, not the manufacturer name; no separate manufacturer lookup is supplied. |
| `DEPARTMENT` | `VARCHAR` | Broad product grouping. | Category label | 15 whitespace-only entries in the saved audit; trim and handle explicitly in staging. |
| `BRAND` | `VARCHAR` | Private-label versus national-label classification. | Category label | Observed values: Private, National. Not a named consumer brand. |
| `COMMODITY_DESC` | `VARCHAR` | Product grouping below department. | Category label | 15 whitespace-only entries in the saved audit. |
| `SUB_COMMODITY_DESC` | `VARCHAR` | More detailed grouping below commodity. | Category label | 15 whitespace-only entries in the saved audit. |
| `CURR_SIZE_OF_PRODUCT` | `VARCHAR` | Recorded package-size description. | Text with product-specific units | Examples may combine a number and a unit. 30,607 whitespace-only entries; do not parse as one universal numeric unit. |

### `hh_demographic.csv`

**Rows in saved audit:** 801. **Grain:** One available household demographic record; household_key uniqueness checked.

Definitions: [demographic reference](https://bradleyboehmke.github.io/completejourney/reference/demographics.html). Raw field names are retained below.

| Column | Inferred type | Meaning | Units / representation | Interpretation and joins |
|---|---|---|---|---|
| `AGE_DESC` | `VARCHAR` | Estimated age band associated with the household record. | Years, categorical band | Observed: 19-24, 25-34, 35-44, 45-54, 55-64, 65+. Not an exact age or the ages of all members. |
| `MARITAL_STATUS_CODE` | `VARCHAR` | Coded marital-status attribute. | Category code | Observed A, B, U. A=married, B=single, U=unknown is supported by the related 84.51? dictionary [M]; preserve raw codes and flag cross-release mapping before recoding. |
| `INCOME_DESC` | `VARCHAR` | Household income band. | Categorical income range | Labels use K for thousands, from Under 15K to 250K+. Preserve bands; exact income and reporting period are not established here. |
| `HOMEOWNER_DESC` | `VARCHAR` | Home ownership / tenure classification. | Category label | Observed: Homeowner, Renter, Probable Owner, Probable Renter, Unknown. Probable categories retain uncertainty. |
| `HH_COMP_DESC` | `VARCHAR` | Household composition classification. | Category label | Observed categories distinguish adults/children and single-adult descriptions; Unknown is an explicit category. |
| `HOUSEHOLD_SIZE_DESC` | `VARCHAR` | Number of household members, grouped at the upper end. | People, categorical count | Observed: 1, 2, 3, 4, 5+. The last category is not exactly five people. |
| `KID_CATEGORY_DESC` | `VARCHAR` | Children-count category. | Children, categorical count | Observed: 1, 2, 3+, None/Unknown. Do not convert None/Unknown into a confirmed zero. |
| `household_key` | `BIGINT` | Household identifier attached to the demographic record. | Identifier | Unique in the initial audit. Only 801 of 2,500 purchasing households have a record; use a left join. |

### `campaign_desc.csv`

**Rows in saved audit:** 30. **Grain:** One campaign record; CAMPAIGN uniqueness checked.

Definitions: [campaign metadata reference](https://bradleyboehmke.github.io/completejourney/reference/campaign_descriptions.html). Raw field names are retained below.

| Column | Inferred type | Meaning | Units / representation | Interpretation and joins |
|---|---|---|---|---|
| `DESCRIPTION` | `VARCHAR` | Campaign-type label. | Category label | Observed: TypeA, TypeB, TypeC. It is not a free-text campaign title; see coupon availability note below. |
| `CAMPAIGN` | `BIGINT` | Campaign identifier. | Identifier | Unique in this file in the initial audit. Retain identifiers from the raw release, not R-package ranges. |
| `START_DAY` | `BIGINT` | Relative campaign start day. | Source day index | Compare on the same relative-day axis as transactions and redemptions; do not assign calendar dates yet. |
| `END_DAY` | `BIGINT` | Relative campaign end day. | Source day index | Campaign validity ends on this source day; verify boundary rules before implementing eligibility. Maximum saved-audit value is 719, beyond transaction day 711. |

### `campaign_table.csv`

**Rows in saved audit:** 7,208. **Grain:** One household/campaign contact; pair uniqueness checked.

Definitions: [campaign contact reference](https://bradleyboehmke.github.io/completejourney/reference/campaigns.html). Raw field names are retained below.

| Column | Inferred type | Meaning | Units / representation | Interpretation and joins |
|---|---|---|---|---|
| `DESCRIPTION` | `VARCHAR` | Type label for the received campaign. | Category label | Same intended meaning as campaign_desc.DESCRIPTION; equality across files has not yet been audited. |
| `household_key` | `BIGINT` | Household recorded as receiving the campaign. | Identifier | Historical contact is not evidence of random treatment assignment. |
| `CAMPAIGN` | `BIGINT` | Received campaign identifier. | Identifier | Join to campaign_desc.CAMPAIGN. Household plus campaign is unique in the initial audit. |

### `coupon.csv`

**Rows in saved audit:** 124,548. **Grain:** One coupon/campaign/product eligibility mapping; candidate composite key not checked.

Definitions: [coupon reference](https://bradleyboehmke.github.io/completejourney/reference/coupons.html). Raw field names are retained below.

| Column | Inferred type | Meaning | Units / representation | Interpretation and joins |
|---|---|---|---|---|
| `COUPON_UPC` | `BIGINT` | Coupon identifier / barcode-like code. | Identifier | Not a product identifier or household identifier. Repeats across eligible products; preserve with CAMPAIGN when matching. |
| `PRODUCT_ID` | `BIGINT` | Product eligible for the coupon in this mapping row. | Identifier | Join to product.PRODUCT_ID; eligibility does not establish that this product was purchased. |
| `CAMPAIGN` | `BIGINT` | Campaign containing the coupon offer. | Identifier | Join to campaign_desc. Candidate mapping key is (CAMPAIGN, COUPON_UPC, PRODUCT_ID); uniqueness not yet checked. |

### `coupon_redempt.csv`

**Rows in saved audit:** 2,318. **Grain:** One recorded household coupon redemption observation; composite uniqueness not checked.

Definitions: [redemption reference](https://bradleyboehmke.github.io/completejourney/reference/coupon_redemptions.html). Raw field names are retained below.

| Column | Inferred type | Meaning | Units / representation | Interpretation and joins |
|---|---|---|---|---|
| `household_key` | `BIGINT` | Household recorded as redeeming the coupon. | Identifier | Can be related to campaign contacts using household plus campaign; relationship completeness remains to be checked. |
| `DAY` | `BIGINT` | Relative day of the recorded redemption. | Source day index | Not a complete timestamp; calendar mapping and validity-window checks remain pending. |
| `COUPON_UPC` | `BIGINT` | Identifier of the redeemed coupon. | Identifier | Use CAMPAIGN plus COUPON_UPC for eligibility mapping. A join to coupon can expand one redemption into many product candidates. |
| `CAMPAIGN` | `BIGINT` | Campaign associated with the redemption. | Identifier | This table has no BASKET_ID, PRODUCT_ID, redemption amount, or redemption quantity. Do not invent an exact receipt-line match. |

### `causal_data.csv`

**Rows in saved audit:** 36,786,524. **Grain:** One recorded promotional placement observation for product/store/week; composite uniqueness not checked.

Definitions: [promotion code reference](https://bradleyboehmke.r-universe.dev/completejourney/doc/completejourney.html#promotions). Raw field names are retained below.

| Column | Inferred type | Meaning | Units / representation | Interpretation and joins |
|---|---|---|---|---|
| `PRODUCT_ID` | `BIGINT` | Product associated with the promotional placement record. | Identifier | Join to product; use product, store, and source week together when relating exposure to purchases. |
| `STORE_ID` | `BIGINT` | Store for the promotional placement. | Identifier | Same intended store identifier as transaction_data.STORE_ID; coverage is not yet fully audited. |
| `WEEK_NO` | `BIGINT` | Source week of the recorded promotional placement. | Source week index | Relate to transaction_data.WEEK_NO. The candidate product/store/week grain still requires uniqueness validation. |
| `display` | `VARCHAR` | Code for additional in-store product placement. | Categorical text code | See code meanings below. Includes letters; do not treat it as a numeric intensity score. |
| `mailer` | `VARCHAR` | Code describing advertisement placement in a mailer. | Categorical text code | See code meanings below. Store-level opportunity for exposure, not proof that a household saw the advertisement. |

## Promotion code meanings

These code definitions are adapted from the package-maintainer [promotion documentation](https://bradleyboehmke.r-universe.dev/completejourney/doc/completejourney.html#promotions). They are a documented lookup, **not a claim that every code occurs in our CSV**. An exhaustive local code-domain audit has not yet been run; preserve and flag any unrecognised code.

| `display` code | Placement interpretation |
|---|---|
| `0` | No additional display recorded |
| `1` | Front area of the store |
| `2` | Back area of the store |
| `3` | Aisle-end placement near the front |
| `4` | Aisle-end placement in the middle area |
| `5` | Aisle-end placement toward the back |
| `6` | Aisle-end placement at a side aisle |
| `7` | Placement within an aisle |
| `9` | Additional display at another location |
| `A` | Placement on a shelf |

| `mailer` code | Advertisement interpretation |
|---|---|
| `0` | No advertisement recorded |
| `A` | Featured offer on an inside page |
| `C` | Listed item on an inside page |
| `D` | Featured offer on the front page |
| `F` | Featured offer on the back page |
| `H` | Featured offer on the front of the wrap |
| `J` | Coupon inside the wrap |
| `L` | Featured offer on the back of the wrap |
| `P` | Coupon on an inside page |
| `X` | Free-product offer on an inside page |
| `Z` | Free-product offer on a front/back page or wrap |

## Sales and discount interpretation

The original guide distinguishes retailer proceeds from customer out-of-pocket spend: manufacturer-coupon funding can cover part of the retailer's receipt. Accordingly, `SALES_VALUE` must not be labelled customer payment or profit. Loyalty and matching adjustments must not be deducted from it again. These are line amounts, not per-unit prices. [Original guide, p. 4](https://manuals.plus/m/ad83946d9648be9e5080c33c4fd2a9b66aace5bbeb875808d390c3f1df872741).

Local audit: 36 rows have at least one positive discount field, 14,466 have zero quantity, and 18,850 have zero sales. Preserve signs and investigate these cases. Price reconstruction and customer-payment formulas are deliberately not implemented here: first validate them against source examples and anomaly handling. No cost-of-goods or margin field is supplied, so profit requires explicit assumptions.

## Campaign availability and join risks

For TypeA campaigns, the coupon mapping is a possible-offer pool; participants received 16 selected coupons, and their exact individual selections are unavailable. For TypeB/TypeC, participants received the campaign's coupon set. This limits offer-level denominators and exposure inference. [Original guide, pp. 5?6](https://manuals.plus/m/ad83946d9648be9e5080c33c4fd2a9b66aace5bbeb875808d390c3f1df872741).

Project modelling rules, pending complete relationship checks:

| Relationship | Intended join | Safeguard |
|---|---|---|
| Purchase ? product | `PRODUCT_ID` | Initial audit found no unmatched purchase rows; do not generalise to every other product relationship. |
| Household ? demographics | `household_key` | Left join from the full household population; retain missing demographic records. |
| Campaign contact ? campaign description | `CAMPAIGN` | Campaign keys and assignment references passed the initial audit. |
| Coupon eligibility ? product / campaign | `PRODUCT_ID` / `CAMPAIGN` | Reference completeness and mapping uniqueness still pending. |
| Redemption ? coupon eligibility | `CAMPAIGN`, `COUPON_UPC` | One redemption can match multiple eligible products; do not sum redemption counts after expansion. |
| Purchase ? promotional placement | `PRODUCT_ID`, `STORE_ID`, `WEEK_NO` | Validate placement uniqueness before joining to avoid multiplying sales rows. |
| Redemption ? purchase candidates | Household, source day and eligible products | No exact receipt-line key is present; matching remains ambiguous. |

## Time, missingness and unresolved definitions

- Observed transaction days end at 711; campaign end days reach 719. Outcomes for later campaigns are incomplete. A 30-day future label requires a cutoff no later than source day 681 under the current observation horizon.
- Source week and source day are separate fields. Calendar origin, week alignment and time zone remain unverified. `TRANS_TIME` as HHMM is a working interpretation consistent with observed strings, not a validated timestamp conversion.
- No SQL NULLs were found in the initial parsing, but whitespace-only product values exist. Explicit labels such as `Unknown`, `None/Unknown`, and `NO COMMODITY DESCRIPTION` can encode semantic missingness even when not NULL. Do not silently treat them as confirmed facts.
- **[M] Marital codes:** a related publisher-authored [84.51? data dictionary hosted by Carnegie Mellon](https://www.stat.cmu.edu/tartandatasciencecup/episodeII/8451_TDSC_Data_Dictionary_Update.pdf) gives A/B/U meanings. It describes a different release with different transaction fields; use it only as cross-release support for those demographic codes, not as a replacement transaction schema.
- No household-level acquisition date, experimental treatment assignment, individual coupon selection for TypeA, product cost, or verified causal uplift is provided by these eight headers. Do not infer them from identifiers or observed purchases.

## Further reading

- [Local data inventory and modelling decisions](data_inventory.md)
- [Initial audit results](../reports/data_quality.md)
- [Executed data-understanding notebook](../notebooks/01_data_understanding.ipynb)
- [Original publisher's dataset portal](https://www.dunnhumby.com/source-files/)
