"Budget-constrained CRM scenario selection, not causal uplift estimation."

from decimal import Decimal
import numpy as np
import pandas as pd


def cents(value):
    amount = Decimal(str(value))
    if amount < 0 or amount != amount.quantize(Decimal(".01")):
        raise ValueError("Budget and cash costs must be nonnegative exact cents")
    return int(amount * 100)


def select_campaign(frame, config):
    c = config
    budget = cents(c["budget_usd"])
    discount = cents(c["discount_usd"])
    contact = cents(c["contact_cost_usd"])
    if (
        discount + contact <= 0
        or not 0 <= c["assumed_absolute_uplift"] <= 1
        or not 0 <= c["gross_margin"] <= 1
    ):
        raise ValueError("Invalid campaign assumptions")
    if not 0 <= c["exclude_baseline_purchase_above"] <= 1:
        raise ValueError("Invalid purchase-probability exclusion threshold")
    if not frame.household_key.is_unique:
        raise ValueError("Campaign input requires one row per household")
    f = frame.copy()
    if not f.risk_probability.between(0, 1).all():
        raise ValueError("Risk probabilities must be finite and in [0,1]")
    f["p0_purchase"] = 1 - f.risk_probability
    f["assumed_p1_purchase"] = np.minimum(
        f.p0_purchase + c["assumed_absolute_uplift"], 1
    )
    f["assumed_incremental_purchase_probability"] = (
        f.assumed_p1_purchase - f.p0_purchase
    )
    f["expected_incremental_profit_usd"] = (
        f.assumed_incremental_purchase_probability
        * f.average_basket_180
        * c["gross_margin"]
        - f.assumed_p1_purchase * (discount / 100)
        - contact / 100
    )
    f["expected_offer_cost_usd"] = (
        f.assumed_p1_purchase * (discount / 100) + contact / 100
    )
    f["worst_case_cost_cents"] = discount + contact
    f["policy_eligible"] = (
        (f.p0_purchase <= c["exclude_baseline_purchase_above"])
        & (f.observed_history_days >= c["minimum_observed_history_days"])
        & (f.average_basket_180 >= discount / 100)
    )
    f["positive_scenario_value"] = f.expected_incremental_profit_usd > 0
    f["selected"] = False
    candidates = f.loc[f.policy_eligible & f.positive_scenario_value].sort_values(
        ["expected_incremental_profit_usd", "household_key"], ascending=[False, True]
    )
    limit = budget // (discount + contact)
    picked = candidates.head(limit)
    f.loc[picked.index, "selected"] = True
    selected = f.loc[f.selected].sort_values(
        ["expected_incremental_profit_usd", "household_key"], ascending=[False, True]
    )
    assert int(selected.worst_case_cost_cents.sum()) <= budget
    summary = {
        "selected_households": len(selected),
        "budget_usd": budget / 100,
        "worst_case_cost_usd": int(selected.worst_case_cost_cents.sum()) / 100,
        "expected_offer_cost_usd": float(selected.expected_offer_cost_usd.sum()),
        "scenario_incremental_profit_usd": float(
            selected.expected_incremental_profit_usd.sum()
        ),
        "policy_eligible_households": int(f.policy_eligible.sum()),
        "positive_value_households": len(candidates),
        "assumed_absolute_uplift": c["assumed_absolute_uplift"],
        "assumed_margin": c["gross_margin"],
        "not_measured": (
            "Offer response, causal uplift, real margin and realised incremental profit"
        ),
    }
    return f, selected, summary


def campaign_sensitivity(frame, config):
    rows = []
    for margin in [0.15, 0.25, 0.35]:
        for uplift in [0, 0.02, 0.05, 0.10]:
            _, _, result = select_campaign(
                frame,
                {**config, "gross_margin": margin, "assumed_absolute_uplift": uplift},
            )
            rows.append({
                "gross_margin": margin,
                "assumed_absolute_uplift": uplift,
                **{
                    k: result[k]
                    for k in [
                        "selected_households",
                        "worst_case_cost_usd",
                        "scenario_incremental_profit_usd",
                    ]
                },
            })
    return pd.DataFrame(rows)


def compare_policies(candidates, selected_count, seed=42):
    pool = candidates.loc[candidates.policy_eligible].copy()
    orders = {
        "scenario_value": pool.sort_values(
            ["expected_incremental_profit_usd", "household_key"],
            ascending=[False, True],
        ),
        "highest_risk": pool.sort_values(
            ["risk_probability", "household_key"], ascending=[False, True]
        ),
        "highest_purchase_probability": pool.sort_values(
            ["p0_purchase", "household_key"], ascending=[False, True]
        ),
        "random": pool.sample(frac=1, random_state=seed),
    }
    return pd.DataFrame([
        {
            "policy": name,
            "selected_households": len(f.head(selected_count)),
            "scenario_incremental_profit_usd": float(
                f.head(selected_count).expected_incremental_profit_usd.sum()
            ),
            "worst_case_cost_usd": float(
                f.head(selected_count).worst_case_cost_cents.sum() / 100
            ),
        }
        for name, f in orders.items()
    ])
