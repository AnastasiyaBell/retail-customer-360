"One-command local refresh through analytics, ML, CRM and BI-ready exports."

import argparse
import hashlib
import json
import platform
from pathlib import Path
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
import sklearn
from retail_customer_360.metrics import (
    ROOT,
    load_transactions,
    build_metrics,
    export_metrics,
)
from retail_customer_360.customer_analytics import (
    create_baskets,
    features_at,
    rfm_segments,
    cluster_customers,
    retention_tables,
    contribution_scenario,
    FEATURES,
)
from retail_customer_360.modeling import train_models, split_cutoffs
from retail_customer_360.crm import (
    select_campaign,
    campaign_sensitivity,
    compare_policies,
)


def save_json(path, value):
    path.write_text(
        json.dumps(
            value,
            indent=2,
            default=lambda x: x.item() if isinstance(x, np.generic) else str(x),
        )
        + "\n",
        encoding="utf-8",
    )


def write_frame(folder, name, frame):
    frame.to_csv(folder / (name + ".csv"), index=False)


def bi_exports(
    con,
    root,
    out,
    latest,
    cohorts,
    retention,
    models,
    clusters,
    scenarios,
    selected,
    crm_summary,
):
    private = out / "bi_private"
    public = out / "bi_public"
    private.mkdir(exist_ok=True)
    public.mkdir(exist_ok=True)
    con.execute(
        "CREATE TEMP TABLE products AS SELECT product_id::BIGINT AS "
        "product_id,\n        "
        "coalesce(nullif(trim(department),''),'[Unknown]') AS "
        "department,\n        "
        "coalesce(nullif(trim(commodity_desc),''),'[Unknown]') AS "
        "category,\n        brand FROM "
        "read_csv(?,header=true,all_varchar=true)",
        [str(root / "data/raw/product.csv")],
    )
    if con.execute("""SELECT count(*)-count(DISTINCT product_id)
FROM products""").fetchone()[0]:
        raise ValueError("Product dimension is not unique")
    con.execute(
        """CREATE TEMP TABLE transaction_context_bi AS
SELECT household_key::BIGINT AS household_key, basket_id::BIGINT AS basket_id,
       day::INTEGER AS day,product_id::BIGINT AS product_id,
       store_id::BIGINT AS store_id,week_no::INTEGER AS source_week,
       quantity::BIGINT AS quantity,sales_value::DECIMAL(18,
                                                   2) AS sales_value
FROM read_csv(?, header=true, all_varchar=true)""",
        [str(root / "data/raw/transaction_data.csv")],
    )
    cutoff = int(latest.cutoff_day.iloc[0])
    con.execute(
        """CREATE TEMP TABLE day_dimension AS
SELECT DISTINCT day,source_week
FROM transaction_context_bi
WHERE day<=?""",
        [cutoff],
    )
    if con.execute("""SELECT count(*)-count(DISTINCT day)
FROM day_dimension""").fetchone()[0]:
        raise ValueError("Day-to-week mapping is ambiguous")
    con.execute(
        """CREATE TEMP TABLE sales_lines_bi AS
SELECT t.household_key,t.basket_id,t.day,t.source_week, t.product_id,
       t.store_id,t.quantity,t.sales_value,
       coalesce(p.category,
         '[Unmatched product]') AS category
FROM transaction_context_bi t
LEFT JOIN products p USING(product_id)
WHERE t.day<=?
  AND t.quantity>0
  AND t.sales_value>0""",
        [cutoff],
    )
    assert (
        con.execute("""SELECT sum(sales_value)
FROM sales_lines_bi""").fetchone()[0]
        == con.execute("""SELECT sum(eligible_sales_value)
FROM all_baskets""").fetchone()[0]
    )
    # Registration avoids replacing household metrics or re-reading household exports.
    con.fetchall()  # Finalise the preceding scalar result before DuckDB registration.
    con.register("latest_snapshot", latest)
    write_frame(private, "household_snapshot", latest)
    for name, query in {
        "sales_lines": (
            """SELECT *
FROM sales_lines_bi
ORDER BY day,basket_id,product_id"""
        ),
        "basket_fact": (
            """SELECT *
FROM all_baskets
ORDER BY day,basket_id"""
        ),
        "dim_day": (
            """SELECT *
FROM day_dimension
ORDER BY day"""
        ),
        "dim_product": (
            """SELECT *
FROM products
ORDER BY product_id"""
        ),
    }.items():
        path = (private / (name + ".csv")).as_posix().replace("'", "''")
        con.execute(f"COPY ({query}) TO '{path}' (HEADER,DELIMITER ',')")
    weekly = con.execute(
        "SELECT w.source_week,s.segment,count(*) AS "
        "paid_baskets,\n        count(DISTINCT b.household_key) AS "
        "weekly_purchasing_households,\n        "
        "sum(b.eligible_sales_value) AS sales_value\n        FROM "
        "all_baskets b JOIN day_dimension w USING(day) JOIN "
        "latest_snapshot s USING(household_key)\n        GROUP BY "
        "w.source_week,s.segment ORDER BY w.source_week,s.segment"
    ).fetchdf()
    coverage = con.execute("""SELECT source_week,count(*) AS observed_days
FROM day_dimension
GROUP BY source_week""").fetchdf()
    weekly = weekly.merge(coverage, on="source_week")
    weekly["snapshot_day"] = cutoff
    category = con.execute(
        """SELECT t.category,s.segment,sum(t.sales_value) AS sales_value,
       count(DISTINCT t.household_key) AS category_purchasing_households
FROM sales_lines_bi t
JOIN latest_snapshot s USING(household_key)
GROUP BY t.category,s.segment
ORDER BY t.category,s.segment"""
    ).fetchdf()
    category["snapshot_day"] = cutoff
    category["observed_households"] = len(latest)
    segment = latest.groupby("segment", as_index=False).agg(
        households=("household_key", "size"),
        monetary_180=("monetary_180", "sum"),
        frequency_180=("frequency_180", "sum"),
        mean_recency=("recency", "mean"),
        scenario_contribution_usd=("scenario_contribution_usd", "sum"),
    )
    segment["snapshot_day"] = cutoff
    scored = latest.loc[latest.risk_probability.notna()].copy()
    scored["risk_band"] = pd.cut(
        scored.risk_probability,
        bins=[-0.000001, 0.2, 0.4, 0.6, 0.8, 1],
        labels=["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"],
    )
    risk = (
        scored.groupby(["segment", "risk_band"], observed=True)
        .size()
        .rename("households")
        .reset_index()
    )
    test = (
        models["test_predictions"]
        .loc[lambda x: x.model == models["manifest"]["selected_model"]]
        .copy()
    )
    test["probability_bin"] = np.minimum((test.risk_probability * 10).astype(int), 9)
    calibration = test.groupby("probability_bin", as_index=False).agg(
        rows=("no_purchase_30d", "size"),
        mean_predicted_risk=("risk_probability", "mean"),
        observed_no_purchase_rate=("no_purchase_30d", "mean"),
    )
    model_metrics = pd.concat(
        [
            models["validation_metrics"].assign(split="validation"),
            models["test_metrics"].assign(split="test"),
        ],
        ignore_index=True,
    )
    selected_segments = selected.groupby("segment", as_index=False).agg(
        selected_households=("household_key", "size"),
        expected_offer_cost_usd=("expected_offer_cost_usd", "sum"),
        scenario_incremental_profit_usd=("expected_incremental_profit_usd", "sum"),
    )
    scenarios = scenarios.copy()
    scenarios["scenario_id"] = [
        "scenario_" + str(i + 1).zfill(2) for i in range(len(scenarios))
    ]
    scenarios["budget_usd"] = crm_summary["budget_usd"]
    public_tables = {
        "weekly_sales": weekly,
        "category_sales": category,
        "segment_summary": segment,
        "cohort_retention": cohorts,
        "period_retention": retention,
        "risk_distribution": risk,
        "model_metrics": model_metrics,
        "calibration_bins": calibration,
        "cluster_summary": clusters,
        "crm_scenarios": scenarios,
        "crm_selected_segments": selected_segments,
    }
    for name, frame in public_tables.items():
        assert "household_key" not in frame.columns
        write_frame(public, name, frame)
    contract = {
        name: {"rows": len(f), "columns": {c: str(t) for c, t in f.dtypes.items()}}
        for name, f in public_tables.items()
    }
    save_json(
        out / "dashboard_manifest.json",
        {
            "snapshot_day": cutoff,
            "public_tables": contract,
            "source_day_axis": "relative source days; no calendar dates assigned",
            "segment_attribution": (
                "latest snapshot applied retrospectively to historical sales; not"
                " historical segment membership"
            ),
            "publication_status": (
                "Prepared locally; no dashboard published. Check source redistribution"
                " terms before any public upload."
            ),
        },
    )
    # Explicit campaign contacts and redemption observations, not causal treatment
    # outcomes.
    campaigns = pd.read_csv(root / "data/raw/campaign_desc.csv").rename(
        columns=str.lower
    )
    contacts = pd.read_csv(root / "data/raw/campaign_table.csv").rename(
        columns=str.lower
    )
    redemptions = pd.read_csv(root / "data/raw/coupon_redempt.csv").rename(
        columns=str.lower
    )
    if (
        not campaigns.campaign.is_unique
        or contacts.duplicated(["household_key", "campaign"]).any()
    ):
        raise ValueError("Campaign source keys are not unique")
    observed = (
        redemptions.loc[redemptions.day <= cutoff]
        .groupby(["household_key", "campaign"])
        .size()
        .rename("observed_redemptions")
        .reset_index()
    )
    contact_fact = contacts.merge(
        campaigns.drop(columns="description"), on="campaign", validate="many_to_one"
    )
    contact_fact = contact_fact.loc[contact_fact.start_day <= cutoff].merge(
        observed, how="left", on=["household_key", "campaign"], validate="one_to_one"
    )
    contact_fact["observed_redemptions"] = contact_fact.observed_redemptions.fillna(
        0
    ).astype(int)
    contact_fact["campaign_end_observed"] = contact_fact.end_day <= cutoff
    write_frame(private, "dim_campaigns", campaigns)
    write_frame(private, "campaign_contacts", contact_fact)
    return contract


def run(root=ROOT, config_path=None, as_of_day=None):
    root = Path(root)
    config = json.loads(
        Path(config_path or root / "config/project.json").read_text(encoding="utf-8")
    )
    out = root / "data/processed/portfolio"
    out.mkdir(parents=True, exist_ok=True)
    con = load_transactions(root)
    try:
        first, last = con.execute("""SELECT min(day),max(day)
FROM raw_transactions""").fetchone()
        cutoff = last if as_of_day is None else int(as_of_day)
        if not first <= cutoff <= last:
            raise ValueError("Cutoff outside observed source coverage")
        split_cutoffs(
            cutoff, config["horizon_days"]
        )  # Validate temporal design before writing snapshots.
        build_metrics(con, first, cutoff, root)
        export_metrics(con, root)
        create_baskets(con, cutoff)
        print("1/6 Metrics refreshed", flush=True)
        latest = rfm_segments(features_at(con, cutoff, config["lookback_days"], root))
        clusters, k_scores, cluster_profile, cluster_meta, cluster_artifact = (
            cluster_customers(latest, config["seed"])
        )
        latest = latest.merge(clusters, on="household_key", validate="one_to_one")
        contribution = contribution_scenario(latest, **config["clv_scenario"])
        latest = latest.merge(
            contribution.drop(columns="monetary_180"),
            on="household_key",
            validate="one_to_one",
        )
        cohorts, retention = retention_tables(con, cutoff)
        for name, frame in {
            "cohort_retention": cohorts,
            "period_retention": retention,
            "kmeans_scores": k_scores,
            "cluster_profile": cluster_profile,
        }.items():
            write_frame(out, name, frame)
        print("2/6 Segments, cohorts and contribution scenario calculated", flush=True)
        models = train_models(con, cutoff, config)
        for name in [
            "validation_metrics",
            "test_metrics",
            "test_predictions",
            "test_by_cutoff",
        ]:
            write_frame(out, name, models[name])
        snapshots = pd.concat(
            [frame.assign(split=name) for name, frame in models["splits"].items()],
            ignore_index=True,
        )
        write_frame(out, "model_snapshots", snapshots)
        latest["risk_probability"] = np.nan
        eligible = latest.recency < config["lookback_days"]
        latest.loc[eligible, "risk_probability"] = models["model"].predict_proba(
            latest.loc[eligible, FEATURES]
        )[:, 1]
        print("3/6 Model evaluation frozen; latest risk scores generated", flush=True)
        crm_input = latest.loc[eligible].copy()
        candidates, selected, crm_summary = select_campaign(crm_input, config["crm"])
        sensitivity = campaign_sensitivity(crm_input, config["crm"])
        policies = compare_policies(candidates, len(selected), config["seed"])
        for name, frame in {
            "household_snapshot": latest,
            "crm_candidates": candidates,
            "crm_targets": selected,
            "crm_sensitivity": sensitivity,
            "crm_policy_comparison": policies,
        }.items():
            write_frame(out, name, frame)
        save_json(out / "crm_summary.json", crm_summary)
        print("4/6 Scenario CRM audience selected within worst-case budget", flush=True)
        bi_exports(
            con,
            root,
            out,
            latest,
            cohorts,
            retention,
            models,
            cluster_profile,
            sensitivity,
            selected,
            crm_summary,
        )
        print(
            "5/6 Private relational and public aggregate BI exports written", flush=True
        )
        artifacts = out / "models"
        artifacts.mkdir(exist_ok=True)
        joblib.dump(models["model"], artifacts / "no_purchase_model.joblib")
        joblib.dump(cluster_artifact, artifacts / "kmeans.joblib")
        save_json(out / "model_manifest.json", models["manifest"])
        sources = {}
        for filename in [
            "transaction_data.csv",
            "product.csv",
            "campaign_desc.csv",
            "campaign_table.csv",
            "coupon_redempt.csv",
        ]:
            path = root / "data/raw" / filename
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            sources[filename] = {
                "bytes": path.stat().st_size,
                "sha256": digest.hexdigest(),
            }
        manifest = {
            "run_utc": datetime.now(timezone.utc).isoformat(),
            "as_of_day": cutoff,
            "config": config,
            "sources": sources,
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "cluster": cluster_meta,
            "model": models["manifest"],
            "crm": crm_summary,
            "stages": (
                "Analytics/ML/CRM/automation implemented. Power BI and Tableau are"
                " build plans, not completed dashboards."
            ),
        }
        save_json(out / "run_manifest.json", manifest)
        print("6/6 Models, parameters and source hashes saved", flush=True)
        return out
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--as-of-day", type=int)
    args = parser.parse_args()
    print("Outputs:", run(config_path=args.config, as_of_day=args.as_of_day))


if __name__ == "__main__":
    main()
