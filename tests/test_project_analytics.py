("Leakage boundaries, censored retention and hard CRM budget semantics.")

import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retail_customer_360.customer_analytics import (
    create_baskets,
    features_at,
    labelled_snapshot,
    retention_tables,
    FEATURES,
)
from retail_customer_360.modeling import split_cutoffs
from retail_customer_360.crm import select_campaign


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.con = duckdb.connect()
        self.con.execute(
            "CREATE TABLE raw_transactions(household_key "
            "BIGINT,basket_id BIGINT,day INTEGER,quantity "
            "BIGINT,sales_value DECIMAL(18,2))"
        )
        self.con.execute("""INSERT INTO raw_transactions
VALUES (1,1,1,1,10),
       (1,2,100,1,20),
       (2,3,70,1,30),
       (1,4,130,1,40),
       (2,5,131,1,50),
       (3,6,105,1,60),
       (4,7,200,1,10)""")
        create_baskets(self.con, 200)

    def tearDown(self):
        self.con.close()

    def test_future_purchases_never_change_past_features(self):
        before = (
            features_at(self.con, 100)
            .sort_values("household_key")
            .reset_index(drop=True)
        )
        self.con.execute("""INSERT INTO all_baskets
VALUES (1,999,110,9999)""")
        after = (
            features_at(self.con, 100)
            .sort_values("household_key")
            .reset_index(drop=True)
        )
        pd.testing.assert_frame_equal(before, after)
        self.assertNotIn(3, before.household_key.to_list())

    def test_label_boundary_is_open_left_closed_right(self):
        frame = labelled_snapshot(self.con, 100, observation_end=200).set_index(
            "household_key"
        )
        self.assertEqual(frame.loc[1, "no_purchase_30d"], 0)
        self.assertEqual(frame.loc[2, "no_purchase_30d"], 1)
        with self.assertRaises(ValueError):
            labelled_snapshot(self.con, 180, observation_end=200)

    def test_partial_retention_period_is_not_zero_filled(self):
        cohort, trend = retention_tables(self.con, 200)
        self.assertTrue(
            cohort.loc[~cohort.observation_complete, "retention_rate"].isna().all()
        )
        self.assertTrue(
            cohort.loc[cohort.observation_complete, "retention_rate"]
            .between(0, 1)
            .all()
        )
        self.assertTrue(
            (
                cohort.loc[
                    (cohort.period_age == 0) & cohort.observation_complete,
                    "retention_rate",
                ]
                == 1
            ).all()
        )

    def test_split_label_windows_do_not_overlap(self):
        splits = split_cutoffs(711)
        self.assertLess(max(splits["train"]) + 30, min(splits["validation"]))
        self.assertLess(max(splits["validation"]) + 30, min(splits["test"]))
        self.assertLessEqual(max(splits["test"]) + 30, 711)


class CRMTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "household_key": [1, 2, 3, 4],
            "risk_probability": [0.9, 0.8, 0.7, 0.05],
            "average_basket_180": [100.0, 90.0, 80.0, 200.0],
            "observed_history_days": [100] * 4,
        })
        self.config = {
            "budget_usd": 4.10,
            "discount_usd": 2.0,
            "contact_cost_usd": 0.05,
            "assumed_absolute_uplift": 0.2,
            "gross_margin": 0.5,
            "exclude_baseline_purchase_above": 0.8,
            "minimum_observed_history_days": 30,
        }

    def test_hard_budget_and_high_baseline_exclusion(self):
        candidates, selected, summary = select_campaign(self.frame, self.config)
        self.assertEqual(len(selected), 2)
        self.assertLessEqual(summary["worst_case_cost_usd"], self.config["budget_usd"])
        self.assertNotIn(4, selected.household_key.to_list())
        self.assertEqual(selected.household_key.to_list(), [1, 2])

    def test_no_assumed_uplift_means_no_profitable_discount(self):
        _, selected, _ = select_campaign(
            self.frame, {**self.config, "assumed_absolute_uplift": 0}
        )
        self.assertTrue(selected.empty)

    def test_invalid_money_and_duplicate_households_are_rejected(self):
        with self.assertRaises(ValueError):
            select_campaign(self.frame, {**self.config, "budget_usd": 4.101})
        with self.assertRaises(ValueError):
            select_campaign(pd.concat([self.frame, self.frame]), self.config)


if __name__ == "__main__":
    unittest.main()
