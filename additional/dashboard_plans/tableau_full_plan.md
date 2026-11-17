# Tableau / Tableau Public implementation plan

**Status:** a detailed build plan and local CSV exports, not a finished `.twbx` or published Tableau dashboard. The preferred portfolio route is an aggregate-only Tableau Public workbook. No Tableau account or publication has been performed.

## 1. Prepare and choose the package

Run `scripts/run_pipeline.py`. Use `data/processed/portfolio/bi_public/` for the public design below. These files have no household identifiers or CRM target lists. Check dataset redistribution terms before uploading derived data. Tableau Public workbooks and source data are public; it creates extracts when publishing, not private access-controlled workbooks. [Official Public FAQ](https://help.tableau.com/current/pro/desktop/en-us/public_faq.htm), [publishing overview](https://help.tableau.com/current/pro/desktop/en-us/publish_overview.htm).

Use `bi_private/` only for a local detailed workbook. Do not connect private household snapshots and then rely on hiding worksheets to protect them during publication.

## 2. Connect CSVs at their existing grains

Create separate data sources for weekly_sales, segment_summary, category_sales, cohort_retention, period_retention, risk_distribution, model_metrics, calibration_bins, cluster_summary, crm_scenarios and crm_selected_segments. Reuse the same source for compatible sheets; do not physically join all eleven tables. No raw dataset upload is needed for the aggregate design.

Set identifiers/segment/category as dimensions; source-week/day/age as integer dimensions; flags as boolean; amounts and rates as numeric measures. Assign no geographic roles and no calendar date parsing to relative days. Set currency formatting to USD. Rename fields for display, but keep original CSV names in calculation definitions below.

## 3. Calculated fields to create

Create each field in the indicated data source, not in an unrelated joined table.

**weekly_sales**

```tableau
// Retailer Sales
SUM([sales_value])

// Paid Baskets
SUM([paid_baskets])

// Average Basket Value
IF SUM([paid_baskets]) > 0 THEN SUM([sales_value]) / SUM([paid_baskets]) END

// Week Coverage: show with source_week in the view
MAX([observed_days])
```

Weekly household counts cannot be added into a period unique-household count. Do not create a card called Total Customers from `SUM(weekly_purchasing_households)`.

**segment_summary**

```tableau
// Latest Snapshot Households
SUM([households])

// Weighted Snapshot Recency
SUM([mean_recency] * [households]) / SUM([households])

// Scenario Contribution - label with assumptions, not Actual CLV
SUM([scenario_contribution_usd])
```

**category_sales**

```tableau
// Category Reach among All Observed Households
SUM([category_purchasing_households]) / MIN([observed_households])
```

Put category on Rows so this is evaluated for one category. `observed_households` is the fixed entire snapshot population (2,500 initially). If segment is filtered, this shows that segment's category purchasers as a fraction of **all** observed households, not the selected segment's penetration. State that in the tooltip. Do not sum household reach across categories. This file covers the entire source horizon: no week slider on this sheet.

**cohort_retention**

```tableau
// Cohort Retention - use one cohort / period-age cell, no grand totals
IF MIN(IIF([observation_complete], 1, 0)) = 1 THEN
    SUM([active_households]) / MIN([cohort_size])
END
```

Rows = discrete cohort_start_day; Columns = discrete period_age. Incomplete/future cells stay null, not zero. Keep source data present, show empty rows/columns where needed, and turn off grand/subtotals. Each cell has one cohort and age; never calculate a total by summing cell percentages.

**period_retention**

```tableau
// Previous-period Buyer Retention
IF SUM([previous_active_households]) > 0 THEN
    SUM([retained_households]) / SUM([previous_active_households])
END
```

Put period_start_day on Columns. These are 30-source-day blocks, not calendar months.

**crm_scenarios**

Create two numeric parameters: `p Margin` with list 0.15, 0.25, 0.35; `p Assumed Uplift` with list 0, 0.02, 0.05, 0.10. Default 0.25 and 0.10.

```tableau
// Chosen Scenario - put True on Filters for cards
ABS([gross_margin] - [p Margin]) < 0.000001
AND ABS([assumed_absolute_uplift] - [p Assumed Uplift]) < 0.000001

// Scenario Contribution Card
IF COUNTD([scenario_id]) = 1 THEN SUM([scenario_incremental_profit_usd]) END

// Selected Contacts Card
IF COUNTD([scenario_id]) = 1 THEN SUM([selected_households]) END

// Worst-case Cost Card
IF COUNTD([scenario_id]) = 1 THEN SUM([worst_case_cost_usd]) END
```

Parameters choose an exported scenario, not a live model refit. Budget and offer amount are fixed by config; change config and rerun Python for different values. Keep `crm_selected_segments` labelled **Default configured scenario only**: it does not recalculate when the sensitivity parameters change. Hide that sheet for non-default selections or place it in a separate default-plan dashboard.

## 4. Build worksheets in order

| Sheet | Data source | Shelves / marks |
|---|---|---|
| KPI Sales | weekly_sales | Text = SUM(sales_value); source-week and segment filters |
| KPI Baskets | weekly_sales | Text = SUM(paid_baskets) |
| KPI AOV | weekly_sales | Text = Average Basket Value |
| Weekly sales | weekly_sales | Columns source_week continuous integer; Rows sales; Bars |
| Weekly baskets | weekly_sales | Columns source_week; Rows baskets; Bars |
| Weekly AOV | weekly_sales | Columns source_week; Rows AOV; Line |
| Segment size | segment_summary | Rows segment; Columns SUM(households); horizontal bars |
| Segment value | segment_summary | Rows segment; Columns SUM(monetary_180); bars |
| Risk mix | risk_distribution | Rows segment; Columns SUM(households); Color risk_band; stacked bars |
| Cohort heatmap | cohort_retention | Rows cohort_start_day; Columns period_age; Square; Color retention; tooltip cohort_size and complete flag |
| Retention trend | period_retention | Columns period_start_day; Rows buyer-retention calculation; Line |
| Category sales | category_sales | Rows category, sorted descending sales; Columns SUM(sales_value); top-15 set |
| Category reach | category_sales | Same category ordering; Columns category reach; percent formatting |
| Model comparison | model_metrics | Rows model; Columns average_precision; split filter single-select test; no SUM of metrics across splits |
| Calibration | calibration_bins | Columns mean_predicted_risk; Rows observed_no_purchase_rate; Circle, rows on Size; add y=x reference as a separate diagonal guide if supported |
| CRM sensitivity | crm_scenarios | Rows gross_margin; Columns assumed_absolute_uplift; Square; Color scenario contribution; Label selected_households |
| CRM cards | crm_scenarios | Chosen Scenario=True; contribution, contacts and worst-case cost text |
| Default target mix | crm_selected_segments | Rows segment; Columns selected_households; fixed default-scenario caption |

For category Top 15, decide whether it is global or recomputed within segment. If recomputed, make the segment filter context before applying a Top N set; disclose it. Do not let a fixed global Top 15 masquerade as a filtered ranking.

## 5. Assemble dashboards

Use fixed desktop size 1280 x 800, tiled horizontal/vertical containers, 24 px outer padding and a consistent top navigation strip. Use #245C83 observed sales, #208778 customer activity, #D77931 assumption labels; grey for unavailable cells. Add a phone layout after desktop QA.

1. **Business overview:** top KPI strip (sales, baskets, AOV); three aligned weekly panels; bottom definitions/footer. Source-week range and latest-segment filter only. Snapshot household card, if included, stays labelled latest snapshot and is not source-week filtered.
2. **Customers:** segment size/value side by side; risk stack; cluster profile table. No historical period slider. Subtitle: snapshot source day 711, 180-day RFM; risk only for active-180-day households.
3. **Retention:** cohort heatmap at 70% canvas width; cohort-size table/definition at right; period-retention line below. Cohort/age controls local; no category/segment filters that were not computed upstream.
4. **Categories and model QA:** ideally two dashboards if space permits. Category source horizon is fixed, with category/segment controls. Model split is its own filter; calibration is selected model's frozen test only.
5. **CRM scenarios:** margin/uplift parameters, scenario cards, heatmap, assumption panel and separately labelled default target mix. Explicitly say estimated under assumptions, not realised profit.

Use dashboard navigation buttons rather than a long scrolling analysis. Tooltips must name the denominator, time window and source-day semantics.

## 6. Actions and filter scope

- Use native filters applied to selected worksheets, not All Worksheets blindly.
- A segment selection action may map source segment to target segment for weekly/category/risk sheets, but must not filter cohort or model sources. Verify mapping manually across separate data sources.
- Source-week filters affect only weekly sheets. Category source has no temporal grain.
- CRM parameter actions can choose an existing scenario. They do not update a default-only target breakdown.
- Add Reset through Revert or a clearly configured reset button/parameter action; validate after saving. Do not claim a reset button exists until implemented.

## 7. Optional private detailed workbook

Use Sales logical relationships to a unique Household snapshot, Product dimension and Day dimension. Use SUM(sales_value)/COUNTD(basket_id) for filtered AOV. A household repeat count can use `{ FIXED [household_key] : COUNTD([basket_id]) }`, with source-day/category filters placed in context if they must affect the FIXED calculation. Count distinct qualifying household IDs, not repeated line rows. Understand Tableau order-of-operations before using LOD filters. [Official LOD overview](https://help.tableau.com/current/pro/desktop/en-us/calculations_calculatedfields_lod_overview.htm).

This detailed mode should not be published with household-level inputs under the aggregate public design. Hiding identifiers from a chart is not removing them from its extract.

## 8. QA and publication checklist

- Full-horizon sales USD 8,057,443.80; baskets 275,539; AOV USD 29.24248037; latest snapshot households 2,500.
- AOV is a ratio of totals, not AVG of household AOV. Category reach denominator is explicitly the entire observed population.
- Segment sales are attributed by latest membership retrospectively. They are not historical segment trajectories.
- Partial cohorts are null, not 0%; T0 is 100% for completed cohorts. No retention totals across ages.
- Model metrics match frozen test CSV. Selected model is recorded in `model_manifest.json`; deployment-fit output is not a test set.
- CRM selection is scenario-only, within worst-case budget, and zero assumed uplift produces no positive-value discount contacts.
- Check all parameter combinations, no-selection states, top-15 behaviour, cross-source filters, reset/navigation, mobile labels and extract field list.
- Inspect every connected data source before publication: no household IDs, target lists or model snapshots. Review data rights separately.
- Publish manually to Tableau Public after those checks, test the public link in a signed-out browser, then add the real link and screenshots to README. Do not add a placeholder URL as if published.

Checked against official Tableau documentation on 2026-11-03. This repository contains no Tableau workbook or public deployment yet.
