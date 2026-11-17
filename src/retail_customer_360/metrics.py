"Reproducible, cutoff-aware descriptive customer metrics; no raw data edits."

import argparse
import json
from decimal import Decimal
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]


def load_transactions(root=ROOT):
    root = Path(root)
    path = root / "data/raw/transaction_data.csv"
    if not path.is_file():
        raise FileNotFoundError(path)
    con = duckdb.connect()
    con.execute("SET memory_limit='1GB'")
    con.execute("SET threads=2")
    temp = (root / "data/processed/duckdb_tmp").as_posix().replace("'", "''")
    con.execute(f"SET temp_directory='{temp}'")
    # Read monetary strings directly into exact decimal amounts, not binary floats.
    con.execute(
        """CREATE TEMP TABLE source_text AS
SELECT *
FROM read_csv(?, header=true, all_varchar=true)""",
        [str(path)],
    )
    # Permit only documented negligible residues on zero-quantity lines.
    # Preserve their original text for inspection before rounding to exact cents.
    con.execute("""CREATE TEMP TABLE monetary_normalization AS
SELECT sales_value AS original_sales_text, quantity AS original_quantity,
       try_cast(sales_value AS DOUBLE) AS source_numeric_value
FROM source_text
WHERE sales_value IS NOT NULL
  AND NOT regexp_full_match(sales_value,
            '-?[0-9]+([.][0-9]{1,2})?')
  AND abs(try_cast(sales_value AS DOUBLE)) < 1e-9
  AND try_cast(quantity AS BIGINT)=0""")
    invalid = con.execute("""SELECT count(*)
FROM source_text
WHERE sales_value IS NULL
  OR (NOT regexp_full_match(sales_value,
            '-?[0-9]+([.][0-9]{1,2})?')
      AND NOT coalesce(abs(try_cast(sales_value AS DOUBLE))<1e-9
                       AND try_cast(quantity AS BIGINT)=0, false))""").fetchone()[0]
    if invalid:
        con.close()
        raise ValueError(
            f"{invalid} sales values violate the validated cents/residue policy"
        )
    con.execute("""CREATE TEMP TABLE raw_transactions AS
SELECT household_key::BIGINT AS household_key, basket_id::BIGINT AS basket_id,
       day::INTEGER AS day, product_id::BIGINT AS product_id,
       quantity::BIGINT AS quantity, sales_value::DECIMAL(18,
                                                    2) AS sales_value
FROM source_text""")
    con.execute("""DROP TABLE source_text""")
    return con


def build_metrics(con, window_start_day=1, as_of_day=None, root=ROOT):
    first_day, last_day = con.execute("""SELECT min(day), max(day)
FROM raw_transactions""").fetchone()
    if first_day is None:
        raise ValueError("No source transactions")
    cutoff = last_day if as_of_day is None else as_of_day
    if not (first_day <= window_start_day <= cutoff <= last_day):
        raise ValueError(f"Require {first_day} <= start <= cutoff <= {last_day}")
    missing = con.execute(
        """SELECT count(*)
FROM raw_transactions
WHERE day <= ?
  AND (household_key IS NULL
       OR basket_id IS NULL
       OR day IS NULL
       OR quantity IS NULL
       OR sales_value IS NULL)""",
        [cutoff],
    ).fetchone()[0]
    # NULL days cannot be placed safely on either side of the cutoff.
    null_days = con.execute("""SELECT count(*)
FROM raw_transactions
WHERE day IS NULL""").fetchone()[0]
    if missing or null_days:
        raise ValueError("Missing fields prevent reliable eligibility or time scoping")
    conflicts = con.execute(
        """SELECT count(*)
FROM
  (SELECT basket_id
   FROM raw_transactions
   WHERE day <= ?
   GROUP BY basket_id
   HAVING count(DISTINCT household_key)>1
   OR count(DISTINCT day)>1)""",
        [cutoff],
    ).fetchone()[0]
    if conflicts:
        raise ValueError("Basket identifiers conflict on household or day")
    con.execute(
        "CREATE OR REPLACE TEMP TABLE "
        "metrics_parameters(window_start_day INTEGER, as_of_day "
        "INTEGER)"
    )
    con.execute(
        """INSERT INTO metrics_parameters
VALUES (?, ?)""",
        [window_start_day, cutoff],
    )
    con.execute((Path(root) / "sql/customer_metrics.sql").read_text(encoding="utf-8"))
    return con


def summary(con, root=ROOT):
    cursor = con.execute(
        (Path(root) / "sql/customer_metrics_summary.sql").read_text(encoding="utf-8")
    )
    return dict(zip([c[0] for c in cursor.description], cursor.fetchone()))


def export_metrics(con, root=ROOT):
    out = Path(root) / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    for name in ["customer_metrics", "basket_metrics"]:
        path = (out / f"{name}.parquet").as_posix().replace("'", "''")
        con.execute(
            f"COPY (SELECT * FROM {name} ORDER BY household_key"
            + (", day, basket_id" if name == "basket_metrics" else "")
            + f") TO '{path}' (FORMAT PARQUET)"
        )
    path = (out / "customer_metrics.csv").as_posix().replace("'", "''")
    con.execute(
        "COPY (SELECT * FROM customer_metrics ORDER BY "
        "household_key) TO '"
        f"{path}"
        "' (HEADER, DELIMITER ',')"
    )
    result = summary(con, root)
    (out / "customer_metrics_summary.json").write_text(
        json.dumps(
            result, indent=2, default=lambda x: str(x) if isinstance(x, Decimal) else x
        )
        + "\n",
        encoding="utf-8",
    )
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-day", type=int, default=1)
    parser.add_argument("--as-of-day", type=int)
    args = parser.parse_args()
    con = load_transactions()
    try:
        build_metrics(con, args.start_day, args.as_of_day)
        print(json.dumps(summary(con), indent=2, default=str))
        print("Local exports:", export_metrics(con))
    finally:
        con.close()


if __name__ == "__main__":
    main()
