# Focused Power BI dashboard plan

Status: implementation plan only; no workbook has been built or published. The business goal is household-specific coupon selection, but current exports support only purchase analysis and one hypothetical-offer audience. Do not label any page Personalised coupon recommendations yet.

## Main pages

| Page | Content | Source/filter limits |
|---|---|---|
| 1 Purchase overview | Sales, paid baskets, AOV; weekly sales/basket trends | Public weekly_sales: week and latest-segment filters. Do not sum weekly distinct households into period unique customers. |
| 2 Households and categories | RFM sizes; category sales/reach; latest risk bands | segment_summary, category_sales, risk_distribution. RFM is a fixed 180-day snapshot. Public category data has no week grain; category filters are local. Risk is not coupon response. |
| 3 Hypothetical CRM offer | Single selected scenario, contacts, maximum budget reserve, scenario contribution; margin/uplift sensitivity | crm_scenarios; default target segment breakdown is fixed to the configured scenario. One assumed USD 2 offer, no COUPON_UPC allocation. |

Model QA can be a small supporting sheet/table, not the headline business dashboard. Retention heatmaps, K-Means profiles and contribution-value pages are excluded from the main build; their full specifications are preserved in the [extended plan](../additional/dashboard_plans/powerbi_full_plan.md).

## Data and calculations

Use the [data contract](../docs/dashboard_data_contract.md). The public aggregate package is in data/processed/portfolio/bi_public. Private line-level tables are for local detailed analysis. Latest segment membership attached to historical sales is not historical segment membership.

- AOV = summed eligible retailer sales / summed paid baskets.
- Snapshot households = sum of segment household counts; independent of the historical week slider.
- Category reach is per category; household reach overlaps across categories.
- Select exactly one CRM scenario for cards; never add alternative scenarios together.
- Scenario contribution is assumption-dependent, not realised profit. The purchase model reflects historical promotion conditions rather than a verified no-offer counterfactual.

For aggregate mode, import compatible tables separately and use single-direction dimension relationships only where grains match. Keep snapshot/model/scenario slicers page-local.

```dax
Sales = SUM(weekly_sales[sales_value])
Paid Baskets = SUM(weekly_sales[paid_baskets])
AOV = DIVIDE([Sales], [Paid Baskets])
Scenario Contribution =
    IF(
        HASONEVALUE(crm_scenarios[scenario_id]),
        SUM(crm_scenarios[scenario_incremental_profit_usd])
    )
```

For private combined category/time analysis, use the detailed Sales/Households/Days/Products star described in the extended plan. Do not join basket facts to product lines one-to-many and then sum duplicated basket sales.

## Acceptance checks

- Full-window sales USD 8,057,443.80; paid baskets 275,539; AOV USD 29.24248037; snapshot household count 2,500.
- Changing week filters must not silently recompute fixed RFM or change unrelated scenario assumptions.
- Default CRM target breakdown stays labelled default only. Costs must respect the configured hard budget.
- Footer states source-day coverage, snapshot/lookback window, eligibility and scenario assumptions.
- No retention, cluster or CLV metric is required to complete these three pages.

## Future coupon-decision page: not implemented

Add only after a genuine household-coupon candidate dataset exists: recommended COUPON_UPC, eligible category/products, reason/ranking, known validity/cost, household contact limits and evaluation. Do not populate this page from the current generic-offer targets as if they were personalised coupon assignments.
