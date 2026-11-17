# Model card: no paid purchase in the next 30 days

## Intended use and exclusions

Rank currently active retail households for analyst review of observed repeat-purchase risk. Do not interpret risk as permanent churn, coupon responsiveness, or individual causal treatment effect. No automated customer contact or production deployment is implemented.

## Target, population and features

Positive label: no eligible paid basket in `(cutoff, cutoff+30]`. A labelled cutoff needs the complete 30-day follow-up. Eligible modelling household: at least one paid basket by cutoff and a paid basket within the previous 180 days.

Predictors: recency; days since first observed paid purchase; receipt counts in 30/60/90/180 days; eligible sales in 30/180 days; distinct paid-purchase days in 180 days; mean paid basket value in 180 days; frequency_30 minus frequency in the preceding 30 days. No household IDs, source cutoff number, demographics, latest RFM classes, future outcomes, or campaign redemptions are predictors.

## Evaluation design

Current train cutoffs: [210, 240, 270, 300, 330, 360, 390, 420].

Validation: [480, 510]; test: [570, 600, 630, 660]. Last test label ends on source day 690. Gap checks enforce train label end < first validation cutoff and validation label end < first test cutoff. Models are fitted only on training for evaluation.

Households recur across periods; this is time-based prediction for known customers. Snapshot rows are not independent individuals. No independent-row confidence interval or unseen-customer generalisation claim is made. The final dataset's future beyond day 711 is unobserved.

## Candidates and selection

Constant training prevalence; scaled recency-only logistic baseline; scaled multivariate logistic regression; Random Forest (200 trees, maximum depth 10, minimum leaf 30, seed 42). No test tuning. Choose highest validation average precision, tie-break by lower Brier score. Current choice: **random_forest**.

AP is used for ranking under a minority no-purchase class; ROC AUC, Brier, log loss, precision/recall at 0.5 and top-10% ranking are also reported. Fixed 0.5 is diagnostic and not the CRM budget policy. Tied constant-prior scores have arbitrary top-decile membership, so its AP/prevalence is the meaningful baseline.

## Frozen test results

- 9,670 household snapshots; no-purchase prevalence 0.1619.
- Selected model: AP 0.5446, ROC AUC 0.8731, Brier 0.0974.
- Recency baseline: AP 0.4889, ROC AUC 0.8126, Brier 0.1103.

Calibration bins and per-cutoff metrics are exported. They do not establish perfect calibration, subgroup fairness or external validity. Impurity feature importance is association with correlated predictors, not causality.

## Deployment fit and refresh

After frozen evaluation, refit the chosen architecture on all completed labelled snapshots for latest scoring. The deployment fit includes the historical test labels, so never evaluate that refitted artefact on them as an untouched test set. A separate train-only evaluation model generated the reported metrics. Current latest risk is scored without an invented future label.

Local model artefacts, labelled snapshots, test predictions, model_manifest and hashed-source run_manifest are under Git-ignored `data/processed/portfolio/`. Load only artefacts produced locally. The model has not been served or externally deployed.

## Limitations and next validation

Source panel comprises frequent shoppers; left-censored histories, period drift, purchase eligibility and missing retailer visits elsewhere can affect predictions. No post-treatment counterfactual is identified. Before operational use: inspect drift and segment-level calibration, validate on another time range/retailer, reconsider recency eligibility, and run a randomised offer experiment for treatment effects.

API references: [RandomForestClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html), [average precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html). Executed results, not documentation examples, support the numbers above.
