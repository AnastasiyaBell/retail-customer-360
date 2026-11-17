# CRM selection assumptions and proposed experiment

The current output is a household list for one hypothetical offer. It does not assign real COUPON_UPC values. Predicted purchase probability reflects historical promotion conditions; using it as p0 without a new offer is an additional scenario assumption.

## Current algorithm

Use predicted baseline purchase probability p0 = 1 - risk. Assume an absolute response increment u and p1=min(p0+u,1). For a single future eligible basket and at most one fixed-dollar redemption:

`incremental_contribution = (p1-p0) * historical_AOV_180 * assumed_margin - p1 * discount - contact_cost`.

Assume the offer is redeemed whenever an offered household purchases. This is an explicit conservative redemption-cost assumption, not estimated redemption propensity. Do not sum gross retailer sales as profit.

Defaults: budget USD 250, discount USD 2, contact USD 0.05, uplift 10 percentage points, margin 25%, no contacts with p0>80%, at least 30 days observed history, historical AOV >= offer value. These values are planning inputs, not fitted facts. A constant uplift does not distinguish persuadable customers from customers who would ignore the coupon.

Reserve discount+contact for every selected household. Equal per-household maximum cost means descending positive incremental scenario value is optimal under the cardinality budget; there is no claim of an unequal-cost general optimiser. Never spend budget on negative-value rows merely to exhaust it. Positive-probability prediction uncertainty is not incorporated in this deterministic scenario. With assumed uplift zero, the selected audience is empty.

Compare to equal-contact random, highest-risk and highest-purchase-probability rankings in the same eligible pool under the same assumptions. Winning that assumed objective does not establish measured uplift. Report the full margin/uplift grid, not just the favourable default result.

## Randomised pilot required

1. Fix eligibility before exposure; assign each household once. Stratify randomisation by segment and baseline-risk band. Allocate offer vs no-offer with a prespecified probability, retaining a control group even among high-risk customers.
2. Define the offer, validity period, redemption conditions, contact channel and maximum liability. Do not use the historical TypeA pool as a known individual coupon exposure list.
3. Primary outcome: 30-day contribution per assigned household, net of actual offer and contact costs; require actual margin/COGS data. Secondary: purchase rate, eligible sales and basket count. Capture returns and non-redemptions, not only successful redeemers.
4. Set a business minimum detectable contribution effect. Estimate sample size using pilot outcome variance, target power and alpha before launch; this repository does not invent a sample-size estimate from unavailable margin variance.
5. Analyse intention-to-treat by assigned arm. Report uncertainty and prespecified segment interactions, guard against multiple comparisons, and track cross-household offer contamination. Do not condition the primary result on redemption.
6. Replace uniform uplift assumptions only after a validated experimental treatment-effect estimate. Keep holdouts and monitor offer cannibalisation, contact fatigue and distribution drift during later rollout.

No message has been sent, customer contacted or campaign launched. The provided target CSV is a local analytical scenario artefact.
