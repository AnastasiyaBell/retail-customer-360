"Metric semantics on controlled receipt lines, including observation boundaries."

import sys
import unittest
from pathlib import Path
from decimal import Decimal
import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retail_customer_360.metrics import build_metrics, summary, load_transactions
import tempfile


class CustomerMetricsTests(unittest.TestCase):
    def setUp(self):
        self.con = duckdb.connect()
        self.con.execute(
            "CREATE TABLE raw_transactions(household_key "
            "BIGINT,basket_id BIGINT,day INTEGER,product_id "
            "BIGINT,quantity BIGINT,sales_value DECIMAL(18,2))"
        )
        self.con.execute("""INSERT INTO raw_transactions
VALUES (1,10,2,100,1,10.00),
       (1,10,2,101,1,5.00),
       (1,11,2,100,1,20.00),
       (1,12,5,100,1,30.00),
       (1,13,8,100,1,999.00),
       (2,20,3,100,0,7.00),
       (3,30,4,100,1,0.00),
       (4,40,1,100,1,4.00),
       (5,50,8,100,1,50.00)""")

    def tearDown(self):
        self.con.close()

    def test_receipt_grain_zero_rules_and_future_exclusion(self):
        build_metrics(self.con, 2, 5)
        result = summary(self.con)
        self.assertEqual(result["observed_households"], 4)
        self.assertEqual(result["purchasing_households"], 1)
        self.assertEqual(result["purchase_baskets"], 3)
        self.assertEqual(result["eligible_sales_value"], Decimal("65.00"))
        self.assertAlmostEqual(result["average_basket_value"], 65 / 3)
        self.assertEqual(result["repeat_buyer_pct"], 100)
        row = self.con.execute(
            """SELECT purchase_days, recency_days, mean_days_between_baskets,
       baskets_per_30_window_days
FROM customer_metrics
WHERE household_key=1"""
        ).fetchone()
        self.assertEqual(row, (2, 0, 1.5, 22.5))
        # First basket has two lines but only one receipt. Same-day repeat gap is zero.
        self.assertEqual(
            self.con.execute("""SELECT eligible_sales_value
FROM basket_metrics
WHERE basket_id=10""").fetchone()[0],
            Decimal("15.00"),
        )
        inactive = self.con.execute(
            """SELECT purchase_baskets, eligible_sales_value, average_basket_value,
       recency_days
FROM customer_metrics
WHERE household_key=4"""
        ).fetchone()
        self.assertEqual(inactive, (0, Decimal("0.00"), None, None))

    def test_same_day_repeats_are_separate_from_multi_day_repeats(self):
        build_metrics(self.con, 2, 2)
        row = self.con.execute(
            """SELECT repeat_buyer,multi_day_buyer,mean_days_between_baskets
FROM customer_metrics
WHERE household_key=1"""
        ).fetchone()
        self.assertEqual(row, (True, False, 0.0))

    def test_negligible_zero_quantity_residue_is_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data/raw"
            path.mkdir(parents=True)
            (path / "transaction_data.csv").write_text(
                "household_key,BASKET_ID,DAY,PRODUCT_ID,Q"
                "UANTITY,SALES_VALUE\n1,10,1,100,0,5.551115E-17\n"
                "1,11,2,100,1,1.25\n"
            )
            con = load_transactions(directory)
            try:
                self.assertEqual(
                    con.execute("""SELECT count(*)
FROM monetary_normalization""").fetchone()[0],
                    1,
                )
                self.assertEqual(
                    con.execute("""SELECT sum(sales_value)
FROM raw_transactions""").fetchone()[0],
                    Decimal("1.25"),
                )
            finally:
                con.close()

    def test_meaningful_fraction_of_cent_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data/raw"
            path.mkdir(parents=True)
            (path / "transaction_data.csv").write_text(
                "household_key,BASKET_ID,DAY,PRODUCT_ID,Q"
                "UANTITY,SALES_VALUE\n1,10,1,100,1,1.234\n"
            )
            with self.assertRaises(ValueError):
                load_transactions(directory)

    def test_invalid_window_fails(self):
        with self.assertRaises(ValueError):
            build_metrics(self.con, 5, 2)
        with self.assertRaises(ValueError):
            build_metrics(self.con, 1, 9)


if __name__ == "__main__":
    unittest.main()
