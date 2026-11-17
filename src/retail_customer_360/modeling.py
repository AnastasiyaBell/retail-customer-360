"Chronological no-purchase modelling. Latest predictions have no observed label."

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    log_loss,
    precision_score,
    recall_score,
)
from retail_customer_360.customer_analytics import FEATURES, labelled_snapshot


def split_cutoffs(as_of_day, horizon=30):
    if horizon != 30:
        raise ValueError("The current feature/label contract requires a 30-day horizon")
    anchor = ((as_of_day - horizon) // 30) * 30
    result = {
        "train": list(range(anchor - 450, anchor - 239, 30)),
        "validation": [anchor - 180, anchor - 150],
        "test": [anchor - 90, anchor - 60, anchor - 30, anchor],
    }
    if min(result["train"]) < 180:
        raise ValueError(
            "At least 660 observed days are required for this fixed evaluation design"
        )
    assert max(result["train"]) + horizon < min(result["validation"])
    assert max(result["validation"]) + horizon < min(result["test"])
    return result


def classification_metrics(y, p):
    y = np.asarray(y)
    p = np.asarray(p)
    if len(np.unique(y)) < 2:
        raise ValueError("Both classes required for evaluation")
    top = max(1, int(np.ceil(0.1 * len(y))))
    indices = np.argsort(-p, kind="stable")[:top]
    return {
        "rows": len(y),
        "no_purchase_prevalence": float(y.mean()),
        "roc_auc": float(roc_auc_score(y, p)),
        "average_precision": float(average_precision_score(y, p)),
        "brier_score": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "precision_at_10pct": float(y[indices].mean()),
        "recall_at_10pct": float(y[indices].sum() / y.sum()),
        "precision_at_05": float(precision_score(y, p >= 0.5, zero_division=0)),
        "recall_at_05": float(recall_score(y, p >= 0.5, zero_division=0)),
    }


def train_models(con, as_of_day, config):
    cutoffs = split_cutoffs(as_of_day, config["horizon_days"])
    splits = {
        name: (
            pd.concat(
                [
                    labelled_snapshot(
                        con,
                        c,
                        config["horizon_days"],
                        config["lookback_days"],
                        as_of_day,
                    )
                    for c in days
                ],
                ignore_index=True,
            )
            .sort_values(["cutoff_day", "household_key"])
            .reset_index(drop=True)
        )
        for name, days in cutoffs.items()
    }
    for name, frame in splits.items():
        if frame.no_purchase_30d.nunique() != 2:
            raise ValueError(f"Both classes required in {name}")
        if not np.isfinite(frame[FEATURES].to_numpy(dtype=float)).all():
            raise ValueError("Non-finite features")
    seed = config["seed"]
    candidates = {
        "constant_prior": DummyClassifier(strategy="prior"),
        "recency_baseline": make_pipeline(
            ColumnTransformer([("recency", StandardScaler(), ["recency"])]),
            LogisticRegression(max_iter=2000, random_state=seed),
        ),
        "logistic_regression": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000, random_state=seed)
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=config["model"]["random_forest_trees"],
            max_depth=10,
            min_samples_leaf=30,
            n_jobs=2,
            random_state=seed,
        ),
    }
    train = splits["train"]
    validation = splits["validation"]
    test = splits["test"]
    validation_rows = []
    for name, model in candidates.items():
        model.fit(train[FEATURES], train.no_purchase_30d)
        p = model.predict_proba(validation[FEATURES])[:, 1]
        validation_rows.append(
            {"model": name, **classification_metrics(validation.no_purchase_30d, p)}
        )
    validation_metrics = pd.DataFrame(validation_rows)
    # Freeze selection before calculating any held-out test results.
    ranked = validation_metrics.loc[
        validation_metrics.model != "constant_prior"
    ].sort_values(
        ["average_precision", "brier_score", "model"], ascending=[False, True, True]
    )
    chosen = str(ranked.iloc[0].model)
    test_rows = []
    prediction_frames = []
    for name, model in candidates.items():
        p = model.predict_proba(test[FEATURES])[:, 1]
        test_rows.append(
            {"model": name, **classification_metrics(test.no_purchase_30d, p)}
        )
        prediction_frames.append(
            test[["household_key", "cutoff_day", "no_purchase_30d"]].assign(
                model=name, risk_probability=p
            )
        )
    predictions = pd.concat(prediction_frames, ignore_index=True)
    per_cutoff = []
    selected_predictions = predictions.loc[predictions.model == chosen]
    for cutoff, frame in selected_predictions.groupby("cutoff_day"):
        per_cutoff.append({
            "cutoff_day": int(cutoff),
            **classification_metrics(frame.no_purchase_30d, frame.risk_probability),
        })
    # A separate deployment fit uses all completed labels. Test metrics above
    # remain frozen.
    completed = pd.concat(list(splits.values()), ignore_index=True)
    production = clone(candidates[chosen]).fit(
        completed[FEATURES], completed.no_purchase_30d
    )
    manifest = {
        "selected_model": chosen,
        "selection_rule": (
            "Maximum validation average precision; then lower Brier score"
        ),
        "features": FEATURES,
        "cutoffs": cutoffs,
        "label_horizon_days": 30,
        "evaluation_fit": "train only",
        "deployment_fit": "train + validation + test, after frozen evaluation",
        "latest_complete_label_end": int(completed.label_end_day.max()),
        "positive_class": "No eligible paid basket in (cutoff, cutoff+30]",
        "population": (
            "Previously purchasing household with a paid basket in the last 180 days"
        ),
        "limitation": (
            "Repeated households across time; evaluation is forecasting known"
            " customers, not unseen-customer generalisation."
        ),
    }
    return {
        "validation_metrics": validation_metrics,
        "test_metrics": pd.DataFrame(test_rows),
        "test_predictions": predictions,
        "test_by_cutoff": pd.DataFrame(per_cutoff),
        "manifest": manifest,
        "model": production,
        "evaluation_model": candidates[chosen],
        "splits": splits,
    }
