# Power BI implementation plan

**Deliverable status:** build instructions and data exports are ready. No `.pbix` has been created, opened, visually tested or published. Estimated build order below is a checklist, not a completed dashboard claim.

## 1. Choose a workbook mode

- **Local detailed workbook:** use `bi_private/` for fully combined period/category filters and unique counts. Keep it local; publish screenshots/PDF for the portfolio if service sharing is unavailable.
- **Public aggregate workbook:** use `bi_public/` with the explicit page-local filter limits below. Do not combine overlapping pre-aggregated household or category basket counts.

All files live under `data/processed/portfolio/`. Read [data contract](../../docs/dashboard_data_contract.md) first. In Power Query, set identifiers to text or whole number consistently, money to fixed decimal, day/week/period to whole number, flags to boolean, probabilities to decimal. Keep source days as integers. Disable automatic date assumptions; do not mark source-day indices as real calendar dates.

## 2. Private model: build the star

1. Import `household_snapshot`, `sales_lines`, `dim_day`, `dim_product`.
2. Rename tables to `Households`, `Sales`, `Days`, `Products`.
3. Create single-direction 1:* relationships: Households[household_key] -> Sales[household_key]; Days[day] -> Sales[day]; Products[product_id] -> Sales[product_id]. Check uniqueness on every 1-side.
4. Hide Sales[category] and use Products[category] as the visible category field. Never connect facts directly or enable both-direction filtering to fix unexplained totals.
5. Do not load `basket_fact` into the line-fact relationship chain. It is a reconciliation source or an alternative fact, not a join to multiply across product lines.
6. Import cohort, period-retention, model, calibration and CRM aggregates as disconnected page-specific tables. Their slicers are local.
7. Optional campaign page: Campaigns[campaign] -> campaign_contacts[campaign]; Households[household_key] -> campaign_contacts[household_key]. Show observed redemptions and incomplete campaigns, not incremental sales.

## 3. Private DAX measures

```dax
Retailer Sales = SUM(Sales[sales_value])
Paid Baskets = DISTINCTCOUNT(Sales[basket_id])
Purchasing Households = DISTINCTCOUNT(Sales[household_key])
Average Basket Value = DIVIDE([Retailer Sales], [Paid Baskets])
Baskets per Purchasing Household = DIVIDE([Paid Baskets], [Purchasing Households])
Repeat Buyers =
    COUNTROWS(
        FILTER(
            VALUES(Sales[household_key]),
            CALCULATE(DISTINCTCOUNT(Sales[basket_id])) >= 2
        )
    )
Repeat Buyer Rate = DIVIDE([Repeat Buyers], [Purchasing Households])
Snapshot Households = COUNTROWS(Households)
Snapshot 180d Sales = SUM(Households[monetary_180])
Scenario Contribution = SUM(Households[scenario_contribution_usd])
```

Date/category filters on `Sales` change the dynamic purchase measures. They do **not** rebuild Households RFM scores, risk or contribution scenarios. Disable irrelevant interactions on the snapshot page. `Scenario Contribution` must have an assumption label, never the title Actual CLV.

## 4. Aggregate-mode measures

Use a separate aggregate workbook or an explicitly separated model; do not relate private/public facts together. Build a unique Segment lookup from segment_summary if sharing a segment slicer between compatible aggregates.

```dax
Aggregate Sales = SUM(weekly_sales[sales_value])
Aggregate Baskets = SUM(weekly_sales[paid_baskets])
Aggregate AOV = DIVIDE([Aggregate Sales], [Aggregate Baskets])
Snapshot Household Total = SUM(segment_summary[households])
Weighted Snapshot Recency =
    DIVIDE(
        SUMX(
            segment_summary,
            segment_summary[mean_recency] * segment_summary[households]
        ),
        SUM(segment_summary[households])
    )
Cohort Retention =
    IF(
        HASONEVALUE(cohort_retention[cohort_period]) &&
        HASONEVALUE(cohort_retention[period_age]) &&
        SELECTEDVALUE(cohort_retention[observation_complete]) = TRUE(),
        DIVIDE(
            MAX(cohort_retention[active_households]),
            MAX(cohort_retention[cohort_size])
        )
    )
CRM Scenario Profit =
    IF(
        HASONEVALUE(crm_scenarios[scenario_id]),
        SUM(crm_scenarios[scenario_incremental_profit_usd])
    )
CRM Scenario Contacts =
    IF(HASONEVALUE(crm_scenarios[scenario_id]), SUM(crm_scenarios[selected_households]))
```

Use SUM(retained_households)/SUM(previous_active_households) only at a selected period grain for the retention line. No unique-period household KPI from summed weekly household counts. No arbitrary budget what-if measure in aggregate mode: available scenarios are enumerated, fixed-budget reruns.

## 5. Page-by-page layout (16:9, 1280 x 720)

Use navy #245C83 for observed sales, teal #208778 for customer activity, orange #D77931 for assumptions/warnings. White background, one decimal for rates, USD labels for money. Show source attribution and snapshot day in the footer. Public category totals have their own entire-horizon subtitle.

| Page | Top row | Main area | Filters / behaviour |
|---|---|---|---|
| 1 Business overview | Sales, baskets, AOV, latest snapshot households | Three aligned weekly panels: sales, baskets, AOV; note edge-week observed_days | Source-week range and latest segment. Category only in private mode. Do not let period filter change snapshot household card. |
| 2 Customer 360 | Snapshot households, 180-day sales, scored-household count | Segment size/value bars, risk-band stack, K-Means profile table | Latest segment only. Explicit 180-day window. Private mode can add household drillthrough; omit on public version. |
| 3 Retention | Definitions banner | Cohort/age heatmap; period-retention line; cohort-size table | Cohort and age/period filters local. Disable totals on cohort matrix. Incomplete cells blank. No category/segment slicer unless recomputed upstream. |
| 4 Categories and model quality | Category sales/rank; selected model name | Category sales/reach side by side; model AP/Brier table and calibration scatter | Category and latest segment apply only to category visuals, not model metrics. Model split single select, default test. No public source-week filter for category file. |
| 5 CRM planning | Scenario selected contacts, worst-case cost, scenario contribution | Margin/uplift scenario heatmap; default target segment bar; assumptions panel | Single-select scenario_id; keep default target segment chart clearly fixed to default configuration, separate from scenario cards. No Actual campaign ROI title. |

A cleaner alternative is to split page 4 into Categories and Model QA, making six pages. Build the five-page MVP first; do not force unrelated charts into unreadable panels.

## 6. Interaction and tooltip specification

- Cross-filter only within compatible grains. Disable cross-highlighting from snapshot charts into cohort/model charts.
- Weekly tooltip: source_week, sales, baskets, weighted AOV, MAX(observed_days), latest-segment attribution note.
- Cohort tooltip: cohort_start_day, age, cohort_size, active_households, observation_complete.
- CRM tooltip: margin, assumed absolute uplift, configured discount/contact cost, budget, scenario-only caveat. The default is in config/project.json; offer amounts are not editable through a public sensitivity ID.
- Buttons: Overview, Customers, Retention, Categories/Model, CRM; one Reset filters bookmark. Add a Methodology tooltip/page with exact definitions.

## 7. Validation before portfolio screenshots

- With full window/all segments, match the data-contract sales, baskets and AOV. Never average row AOVs.
- Category filtered sales use line amounts; repeat buyers count eligible baskets within that category/time context in private mode.
- Segment counts total 2,500. Latest segment does not change when source-week selection changes.
- Cohort T0 is 100% for completed cohorts; future/partial cells stay blank. Matrix grand totals disabled.
- Test model metrics match pipeline CSV, not deployment-refit predictions on training rows.
- One CRM scenario selected; scenario cards never add all twelve alternative scenarios. Worst-case cost <= configured budget.
- Switching an aggregate category filter does not silently change overview AOV. Default-target chart stays labelled default scenario.
- Compare at least three filtered visual totals with exported CSV queries. Check desktop/mobile canvas, labels and reset behaviour manually.

## 8. Sharing options

Power BI Desktop supports local authoring; interactive service distribution depends on account, licence and tenant settings. Publish to web is a separate **public** publishing path, with no viewer authentication, and is not the same as secure sharing. Its licence/workspace prerequisites and administrator controls must be checked for your account. Use screenshots/PDF and this implementation plan in GitHub if you do not have a suitable service route. Do not upload private household/model tables as an accidental workaround.

Official references: [Publish to web](https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-publish-to-web), [distribution and sharing](https://learn.microsoft.com/power-bi/guidance/powerbi-implementation-planning-content-distribution-sharing), [DAX DIVIDE](https://learn.microsoft.com/en-us/dax/divide-function-dax). Checked 2026-11-03. No account configuration or publication has been performed.
