"""RFM, observed retention and explicit contribution-value scenarios."""

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.preprocessing import StandardScaler
from retail_customer_360.metrics import ROOT

FEATURES = [
    "recency",
    "observed_history_days",
    "frequency_30",
    "frequency_60",
    "frequency_90",
    "frequency_180",
    "monetary_30",
    "monetary_180",
    "purchase_days_180",
    "average_basket_180",
    "frequency_trend_30",
]


def create_baskets(con, as_of_day):
    con.execute(
        """CREATE OR REPLACE TEMP TABLE all_baskets AS
SELECT household_key,basket_id,day,
       sum(sales_value) AS eligible_sales_value
FROM raw_transactions
WHERE quantity>0
  AND sales_value>0
  AND day<=?
GROUP BY household_key,basket_id,day""",
        [int(as_of_day)],
    )


def features_at(con, cutoff, lookback=180, root=ROOT):
    if lookback != 180:
        raise ValueError(
            "Current frequency_180 feature contract requires lookback_days=180"
        )
    query = (
        (Path(root) / "sql/customer_features.sql")
        .read_text()
        .format(cutoff=int(cutoff), lookback=int(lookback))
    )
    frame = con.execute(query).fetchdf()
    frame["average_basket_180"] = np.divide(
        frame.monetary_180,
        frame.frequency_180,
        out=np.zeros(len(frame)),
        where=frame.frequency_180.to_numpy() > 0,
    )
    frame["frequency_trend_30"] = frame.frequency_30 - (
        frame.frequency_60 - frame.frequency_30
    )
    return frame


def labelled_snapshot(con, cutoff, horizon=30, lookback=180, observation_end=None):
    if observation_end is None:
        observation_end = con.execute("""SELECT max(day)
FROM raw_transactions""").fetchone()[0]
    if cutoff + horizon > observation_end:
        raise ValueError("Incomplete future outcome window")
    frame = features_at(con, cutoff, lookback)
    frame = frame.loc[frame.recency < lookback].copy()
    future = (
        con.execute(
            """SELECT DISTINCT household_key
FROM all_baskets
WHERE day>?
  AND day<=?""",
            [int(cutoff), int(cutoff + horizon)],
        )
        .fetchdf()
        .household_key
    )
    frame["no_purchase_30d"] = (~frame.household_key.isin(future)).astype(int)
    frame["label_end_day"] = int(cutoff + horizon)
    return frame


def rfm_segments(frame):
    frame = frame.copy()
    active = frame.frequency_180 > 0
    for field, name, ascending in [
        ("recency", "r_score", False),
        ("frequency_180", "f_score", True),
        ("monetary_180", "m_score", True),
    ]:
        frame[name] = 1
        # Equal values get equal scores; quintiles need not contain equal counts.
        ranks = frame.loc[active, field].rank(
            method="average", pct=True, ascending=ascending
        )
        frame.loc[active, name] = np.ceil(ranks * 5).clip(1, 5).astype(int)
    frame["segment"] = np.select(
        [
            frame.observed_history_days <= 30,
            (frame.r_score >= 4) & (frame.f_score >= 4) & (frame.m_score >= 4),
            (frame.r_score >= 3) & (frame.f_score >= 4),
            (frame.recency > 30) & (frame.f_score >= 3),
            frame.recency > 90,
            (frame.r_score >= 4) & (frame.f_score <= 2),
        ],
        [
            "Newly observed",
            "Champions",
            "Loyal",
            "At risk",
            "Hibernating",
            "Potential loyalists",
        ],
        default="Occasional",
    )
    # No recent paid activity must not be described as an active new customer.
    frame.loc[~active, "segment"] = "Hibernating"
    return frame


def cluster_customers(frame, seed=42):
    active = frame.loc[frame.frequency_180 > 0].copy()
    columns = ["recency", "frequency_180", "monetary_180"]
    if len(active) < 10:
        raise ValueError("Insufficient active households for exploratory K-Means")
    scaler = StandardScaler()
    x = scaler.fit_transform(np.log1p(active[columns].to_numpy(dtype=float)))
    models = {}
    rows = []
    for k in range(2, 7):
        model = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(x)
        models[k] = model
        rows.append({
            "k": k,
            "silhouette": silhouette_score(
                x, model.labels_, sample_size=min(2000, len(x)), random_state=seed
            ),
            "inertia": model.inertia_,
        })
    scores = pd.DataFrame(rows)
    chosen = int(
        scores.sort_values(["silhouette", "k"], ascending=[False, True]).iloc[0].k
    )
    model = models[chosen]
    second = KMeans(n_clusters=chosen, n_init=10, random_state=seed + 1).fit(x)
    stability = float(adjusted_rand_score(model.labels_, second.labels_))
    active["cluster"] = model.labels_.astype(int)
    result = frame[["household_key"]].merge(
        active[["household_key", "cluster"]], how="left", on="household_key"
    )
    result["cluster"] = result.cluster.fillna(-1).astype(int)
    profile = (
        active.groupby("cluster")
        .agg(
            households=("household_key", "size"),
            median_recency=("recency", "median"),
            median_frequency_180=("frequency_180", "median"),
            median_monetary_180=("monetary_180", "median"),
        )
        .reset_index()
    )
    return (
        result,
        scores,
        profile,
        {"chosen_k": chosen, "seed_stability_adjusted_rand": stability},
        {"scaler": scaler, "model": model, "columns": columns},
    )


def retention_tables(con, as_of_day, period_days=30):
    baskets = con.execute(
        """SELECT DISTINCT household_key,day
FROM all_baskets
WHERE day<=?""",
        [int(as_of_day)],
    ).fetchdf()
    baskets["period"] = (baskets.day - 1) // period_days
    first = baskets.groupby("household_key").day.min()
    cohort = ((first - 1) // period_days).rename("cohort_period")
    activity = (
        baskets[["household_key", "period"]]
        .drop_duplicates()
        .merge(cohort, on="household_key")
    )
    sizes = cohort.value_counts().to_dict()
    counts = activity.groupby(["cohort_period", "period"]).size().to_dict()
    rows = []
    for c, size in sorted(sizes.items()):
        for p in range(int(c), (as_of_day - 1) // period_days + 1):
            complete = (p + 1) * period_days <= as_of_day
            n = int(counts.get((c, p), 0))
            rows.append({
                "cohort_period": int(c),
                "cohort_start_day": int(c * period_days + 1),
                "cohort_size": int(size),
                "period": p,
                "period_age": int(p - c),
                "period_end_day": int((p + 1) * period_days),
                "observation_complete": complete,
                "active_households": n,
                "retention_rate": n / size if complete else np.nan,
            })
    sets = {int(p): set(f.household_key) for p, f in baskets.groupby("period")}
    trends = []
    for p in range(1, as_of_day // period_days):
        previous = sets.get(p - 1, set())
        current = sets.get(p, set())
        retained = len(previous & current)
        trends.append({
            "period": p,
            "period_start_day": p * period_days + 1,
            "previous_active_households": len(previous),
            "current_active_households": len(current),
            "retained_households": retained,
            "retention_rate": retained / len(previous) if previous else np.nan,
        })
    return pd.DataFrame(rows), pd.DataFrame(trends)


def contribution_scenario(
    frame, months=6, gross_margin=0.25, monthly_survival=0.9, annual_discount_rate=0.1
):
    if (
        months < 1
        or not 0 <= gross_margin <= 1
        or not 0 <= monthly_survival <= 1
        or annual_discount_rate < 0
    ):
        raise ValueError("Invalid contribution scenario assumptions")
    out = frame[["household_key", "monetary_180"]].copy()
    monthly_discount = (1 + annual_discount_rate) ** (1 / 12) - 1
    multiplier = sum(
        monthly_survival**m / (1 + monthly_discount) ** m for m in range(1, months + 1)
    )
    out["scenario_contribution_usd"] = out.monetary_180 / 6 * gross_margin * multiplier
    out["horizon_months"] = months
    out["assumed_gross_margin"] = gross_margin
    out["assumed_monthly_survival"] = monthly_survival
    return out
