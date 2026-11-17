"Validated category/discount joins and purchase-observed promotion matching."

from pathlib import Path
from retail_customer_360.metrics import ROOT


def add_eda_sources(con, root=ROOT, include_placements=False):
    root = Path(root)
    # Sales cents were validated by load_transactions before this function.
    con.execute(
        "CREATE TEMP TABLE transaction_context AS SELECT\n        "
        "household_key::BIGINT AS household_key,basket_id::BIGINT AS "
        "basket_id,\n        day::INTEGER AS day,product_id::BIGINT "
        "AS product_id,\n        quantity::BIGINT AS "
        "quantity,sales_value::DECIMAL(18,2) AS "
        "sales_value,\n        store_id::BIGINT AS "
        "store_id,week_no::INTEGER AS week_no,\n        "
        "retail_disc::DOUBLE AS retail_disc_raw,coupon_disc::DOUBLE "
        "AS coupon_disc_raw,\n        coupon_match_disc::DOUBLE AS "
        "coupon_match_disc_raw\n        FROM "
        "read_csv(?,header=true,all_varchar=true)",
        [str(root / "data/raw/transaction_data.csv")],
    )
    bad_keys = con.execute("""SELECT count(*)
FROM transaction_context
WHERE store_id IS NULL
  OR week_no IS NULL
  OR product_id IS NULL""").fetchone()[0]
    inconsistent = con.execute("""SELECT count(*)
FROM
  (SELECT basket_id
   FROM transaction_context
   GROUP BY basket_id
   HAVING count(DISTINCT store_id)>1
   OR count(DISTINCT week_no)>1)""").fetchone()[0]
    if bad_keys or inconsistent:
        raise ValueError("Missing product/store/week or inconsistent receipt context")
    for field in ["retail_disc", "coupon_disc", "coupon_match_disc"]:
        invalid = con.execute(f"""SELECT count(*) FROM transaction_context
            WHERE {field}_raw IS NULL OR NOT isfinite({field}_raw)
                OR abs({field}_raw-round({field}_raw,2))>1e-9""").fetchone()[0]
        if invalid:
            raise ValueError(f"Unexpected missing/non-cent discount amounts: {field}")
    con.execute(
        "CREATE TEMP TABLE product_metadata AS SELECT "
        "product_id::BIGINT AS product_id,\n        "
        "coalesce(nullif(trim(department),''),'[Unknown "
        "department]') AS department,\n        CASE WHEN "
        "trim(commodity_desc)='' OR commodity_desc IS "
        "NULL\n             OR trim(commodity_desc)='NO COMMODITY "
        "DESCRIPTION' THEN '[Unknown category]'\n             ELSE "
        "trim(commodity_desc) END AS category\n        FROM "
        "read_csv(?,header=true,all_varchar=true)",
        [str(root / "data/raw/product.csv")],
    )
    duplicates = con.execute("""SELECT count(*)
FROM
  (SELECT product_id
   FROM product_metadata
   GROUP BY product_id
   HAVING count(*)>1)""").fetchone()[0]
    if duplicates:
        raise ValueError("Duplicate product keys would multiply sales")
    if include_placements:
        source = (root / "data/raw/causal_data.csv").as_posix().replace("'", "''")
        con.execute(
            "CREATE VIEW promotion_source AS SELECT * FROM read_csv('"
            f"{source}"
            "',\n            header=true,delim=',',"
            "columns={'PRODUCT_ID':'BIGINT',"
            "'STORE_ID':'BIGINT',\n            'WEEK_NO':'INTEGER',"
            "'display':'VARCHAR','mailer':'VARCHAR'})"
        )
    con.execute((root / "sql/sales_promotions_eda.sql").read_text(encoding="utf-8"))


def build_promotion_match(con):
    "Validate only keys needed by eligible purchases; do not expand duplicate keys."
    con.execute("""CREATE TEMP TABLE needed_promotion_keys AS
SELECT DISTINCT product_id,store_id,week_no
FROM eda_lines""")
    con.execute(
        "CREATE TEMP TABLE promotion_key_audit AS\n        SELECT "
        "s.product_id,s.store_id,s.week_no,count(*) AS "
        "source_rows,\n            count(DISTINCT s.display) AS "
        "display_variants,\n            count(DISTINCT s.mailer) AS "
        "mailer_variants,\n            CASE WHEN count(*)=1 THEN "
        "min(s.display) END AS display,\n            CASE WHEN "
        "count(*)=1 THEN min(s.mailer) END AS mailer\n        FROM "
        "promotion_source s SEMI JOIN needed_promotion_keys "
        "k\n            USING(product_id,store_id,week_no)\n        "
        "GROUP BY s.product_id,s.store_id,s.week_no"
    )
    con.execute("""CREATE TEMP TABLE eda_promotion_lines AS
SELECT l.*,
       CASE
           WHEN p.source_rows IS NULL THEN 'not_recorded'
           WHEN p.source_rows>1 THEN 'ambiguous_key' ELSE 'matched_unique'
       END AS match_status,
       CASE
           WHEN p.source_rows IS NULL THEN '[Not recorded]'
           WHEN p.source_rows>1 THEN '[Ambiguous key]'
           ELSE coalesce(nullif(trim(p.display),
                           ''),
                  '[Missing code]')
       END AS display_code,
       CASE
           WHEN p.source_rows IS NULL THEN '[Not recorded]'
           WHEN p.source_rows>1 THEN '[Ambiguous key]'
           ELSE coalesce(nullif(trim(p.mailer),
                           ''),
                  '[Missing code]')
       END AS mailer_code
FROM eda_lines l
LEFT JOIN promotion_key_audit p USING(product_id,store_id,
                                      week_no)""")
    before = con.execute("""SELECT count(*),sum(sales_value)
FROM eda_lines""").fetchone()
    after = con.execute("""SELECT count(*),sum(sales_value)
FROM eda_promotion_lines""").fetchone()
    if before != after:
        raise AssertionError("Promotion join changed line counts or sales")
