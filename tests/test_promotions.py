("Guard against join inflation and misclassifying positive adjustments.")

import sys
import unittest
from pathlib import Path
from decimal import Decimal
import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retail_customer_360.promotions import build_promotion_match, add_eda_sources
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class PromotionTests(unittest.TestCase):
    def test_duplicate_missing_and_explicit_zero_codes_preserve_sales(self):
        con = duckdb.connect()
        try:
            con.execute(
                "CREATE TABLE eda_lines(product_id BIGINT,store_id BIGINT,week_no"
                " INTEGER,sales_value DECIMAL(18,2))"
            )
            con.execute("""INSERT INTO eda_lines
VALUES (1,10,1,10),
       (2,10,1,20),
       (3,10,1,30),
       (4,10,1,40)""")
            con.execute(
                "CREATE TABLE promotion_source(product_id BIGINT,store_id "
                "BIGINT,week_no INTEGER,display VARCHAR,mailer VARCHAR)"
            )
            con.execute("""INSERT INTO promotion_source
VALUES (1,10,1,'A','A'),
       (1,10,1,'A','A'),
       (2,10,1,'0','0'),
       (4,10,1,NULL,'0')""")
            build_promotion_match(con)
            self.assertEqual(
                con.execute("""SELECT count(*),sum(sales_value)
FROM eda_promotion_lines""").fetchone(),
                (4, Decimal("100.00")),
            )
            rows = dict(con.execute("""SELECT product_id,display_code
FROM eda_promotion_lines""").fetchall())
            self.assertEqual(
                rows,
                {
                    1: "[Ambiguous key]",
                    2: "0",
                    3: "[Not recorded]",
                    4: "[Missing code]",
                },
            )
        finally:
            con.close()

    def test_categories_and_discounts_do_not_require_placement_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "data/raw"
            raw.mkdir(parents=True)
            (root / "sql").mkdir()
            (root / "sql/sales_promotions_eda.sql").write_text(
                (ROOT / "sql/sales_promotions_eda.sql").read_text()
            )
            (raw / "transaction_data.csv").write_text(
                "household_key,BASKET_ID,DAY,PRODUCT_ID,Q"
                "UANTITY,SALES_VALUE,STORE_ID,WEEK_NO,RET"
                "AIL_DISC,COUPON_DISC,COUPON_MATCH_DISC\n"
                "1,10,1,100,1,12.34,20,1,-1,0,0\n"
            )
            (raw / "product.csv").write_text(
                "PRODUCT_ID,DEPARTMENT,COMMODITY_DESC\n100,GROCERY,BREAD\n"
            )
            con = duckdb.connect()
            try:
                con.execute(
                    """CREATE TABLE metrics_parameters(
                    window_start_day INTEGER, as_of_day INTEGER)"""
                )
                con.execute("""INSERT INTO metrics_parameters
VALUES (1,1)""")
                add_eda_sources(con, root)
                self.assertEqual(
                    con.execute("""SELECT count(*),sum(sales_value)
FROM eda_lines""").fetchone(),
                    (1, Decimal("12.34")),
                )
                self.assertFalse((raw / "causal_data.csv").exists())
                self.assertNotIn(
                    "promotion_source",
                    [r[0] for r in con.execute("SHOW TABLES").fetchall()],
                )
            finally:
                con.close()

    def test_positive_adjustments_are_not_counted_as_discount_reductions(self):
        con = duckdb.connect()
        try:
            con.execute(
                """CREATE TABLE metrics_parameters(
                    window_start_day INTEGER, as_of_day INTEGER)"""
            )
            con.execute("""INSERT INTO metrics_parameters
VALUES (1,2)""")
            con.execute(
                "CREATE TABLE product_metadata(product_id BIGINT,department"
                " VARCHAR,category VARCHAR)"
            )
            con.execute("""INSERT INTO product_metadata
VALUES (1,'Food','Bread')""")
            con.execute(
                "CREATE TABLE transaction_context(household_key BIGINT,"
                "basket_id BIGINT,day INTEGER,product_id BIGINT,store_id "
                "BIGINT,week_no INTEGER,quantity BIGINT,sales_value "
                "DECIMAL(18,2),retail_disc_raw DOUBLE,coupon_disc_raw DOUBLE,"
                "coupon_match_disc_raw DOUBLE)"
            )
            con.execute("""INSERT INTO transaction_context
VALUES (1,10,1,1,20,1,1,10,-1,-.5,-.2),
       (1,11,2,1,20,1,1,20,2,0,0),
       (1,12,2,1,20,1,0,30,-9,-9,-9)""")
            con.execute((ROOT / "sql/sales_promotions_eda.sql").read_text())
            row = con.execute(
                """SELECT has_loyalty_reduction, has_positive_adjustment,
                    loyalty_reduction
FROM discount_baskets
WHERE basket_id=11"""
            ).fetchone()
            self.assertEqual(row, (False, True, Decimal("0.00")))
            row = con.execute(
                """SELECT has_loyalty_reduction,has_manufacturer_coupon,has_coupon_match
FROM discount_baskets
WHERE basket_id=10"""
            ).fetchone()
            self.assertEqual(row, (True, True, True))
            self.assertEqual(
                con.execute("""SELECT count(*)
FROM discount_baskets""").fetchone()[0],
                2,
            )
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()
