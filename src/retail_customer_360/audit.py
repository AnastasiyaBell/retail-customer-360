"Shared read-only data audit queries and command-line report generation."

import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_FILES = [
    "campaign_desc",
    "campaign_table",
    "causal_data",
    "coupon",
    "coupon_redempt",
    "hh_demographic",
    "product",
    "transaction_data",
]


def connect_sources(root=ROOT):
    """Expose original CSVs as views without modifying source files."""
    root = Path(root)
    con = duckdb.connect()
    con.execute("SET memory_limit='1GB'")
    con.execute("SET threads=2")
    temp = (root / "data/processed/duckdb_tmp").as_posix().replace("'", "''")
    con.execute(f"SET temp_directory='{temp}'")
    for name in EXPECTED_FILES:
        path = root / "data/raw" / f"{name}.csv"
        if not path.is_file():
            con.close()
            raise FileNotFoundError(path)
        escaped = path.as_posix().replace("'", "''")
        con.execute(
            f"CREATE VIEW {name} AS SELECT * FROM read_csv_auto('{escaped}',"
            " sample_size=-1)"
        )
    return con


def profiling_sql(con, table):
    ("Return the actual SQL used for row counts, NULLs, and blank strings.")
    if table not in EXPECTED_FILES:
        raise ValueError(f"Unknown source table: {table}")
    columns = con.execute(f"DESCRIBE {table}").fetchall()
    aggregates = ["count(*) AS row_count"]
    for i, col in enumerate(columns):
        quoted = '"' + col[0].replace('"', '""') + '"'
        aggregates.append(f"count(*) FILTER (WHERE {quoted} IS NULL) AS null_{i}")
        aggregates.append(
            f"count(*) FILTER (WHERE {quoted} IS NOT NULL AND trim(cast({quoted} AS"
            f" VARCHAR)) = '') AS blank_{i}"
        )
    return "SELECT\n    " + ",\n    ".join(aggregates) + f"\nFROM {table}"


def profile_file(con, table, root=ROOT):
    columns = con.execute(f"DESCRIBE {table}").fetchall()
    values = con.execute(profiling_sql(con, table)).fetchone()
    path = Path(root) / "data/raw" / f"{table}.csv"
    return {
        "rows": values[0],
        "bytes": path.stat().st_size,
        "columns": [
            {
                "name": col[0],
                "inferred_type": col[1],
                "nulls": values[1 + 2 * i],
                "blank_strings": values[2 + 2 * i],
            }
            for i, col in enumerate(columns)
        ],
    }


QUERIES = {
    "transaction_overview": (
        "SELECT min(day) AS first_day, max(day) AS last_day,\n "
        "count(DISTINCT household_key) AS households, count(DISTINCT "
        "basket_id) AS baskets,\n count(DISTINCT product_id) AS "
        "products, count(DISTINCT store_id) AS stores,\n "
        "sum(sales_value) AS source_sales_value_sum,\n count(*) "
        "FILTER (WHERE quantity < 0) AS negative_quantity_rows,\n "
        "count(*) FILTER (WHERE quantity = 0) AS "
        "zero_quantity_rows,\n count(*) FILTER (WHERE sales_value < "
        "0) AS negative_sales_rows,\n count(*) FILTER (WHERE "
        "sales_value = 0) AS zero_sales_rows,\n count(*) FILTER "
        "(WHERE retail_disc > 0 OR coupon_disc > 0 OR "
        "coupon_match_disc > 0) AS positive_discount_rows\n FROM "
        "transaction_data"
    ),
    "transaction_exact_duplicates": (
        """SELECT count(*) AS duplicate_groups, coalesce(sum(n-1),
                                       0) AS excess_rows
FROM
  (SELECT *, count(*) AS n
   FROM transaction_data
   GROUP BY ALL
   HAVING count(*) > 1)"""
    ),
    "product_key_duplicates": (
        """SELECT count(*) AS duplicate_keys
FROM
  (SELECT product_id
   FROM product
   GROUP BY product_id
   HAVING count(*)>1)"""
    ),
    "demographic_key_duplicates": (
        """SELECT count(*) AS duplicate_keys
FROM
  (SELECT household_key
   FROM hh_demographic
   GROUP BY household_key
   HAVING count(*)>1)"""
    ),
    "campaign_key_duplicates": (
        """SELECT count(*) AS duplicate_keys
FROM
  (SELECT campaign
   FROM campaign_desc
   GROUP BY campaign
   HAVING count(*)>1)"""
    ),
    "campaign_assignment_duplicates": (
        """SELECT count(*) AS duplicate_keys
FROM
  (SELECT household_key,campaign
   FROM campaign_table
   GROUP BY ALL
   HAVING count(*)>1)"""
    ),
    "basket_consistency": (
        """SELECT count(*) AS inconsistent_baskets
FROM
  (SELECT basket_id
   FROM transaction_data
   GROUP BY basket_id
   HAVING count(DISTINCT household_key)>1
   OR count(DISTINCT day)>1
   OR count(DISTINCT store_id)>1)"""
    ),
    "product_reference": (
        """SELECT count(*) AS unmatched_transaction_rows
FROM transaction_data t ANTI
JOIN product p USING(product_id)"""
    ),
    "demographic_coverage": (
        "SELECT count(*) AS purchasing_households, "
        "count(d.household_key) AS with_demographics FROM\n (SELECT "
        "DISTINCT household_key FROM transaction_data) t LEFT JOIN "
        "hh_demographic d USING(household_key)"
    ),
    "campaign_reference": (
        """SELECT count(*) AS unmatched_assignments
FROM campaign_table t ANTI
JOIN campaign_desc d USING(campaign)"""
    ),
    "campaign_periods": (
        """SELECT min(start_day) AS first_start_day, max(end_day) AS last_end_day,
       count(*) FILTER (
                        WHERE end_day < start_day) AS invalid_periods
FROM campaign_desc"""
    ),
}


def main():
    REPORTS = ROOT / "reports"
    REPORTS.mkdir(exist_ok=True)
    con = connect_sources()
    profile = {}
    for name in EXPECTED_FILES:
        profile[name] = profile_file(con, name)
        print(f"{name}: {profile[name]['rows']:,} rows", flush=True)
    checks = {}
    for name, query in QUERIES.items():
        cursor = con.execute(query)
        names = [col[0] for col in cursor.description]
        checks[name] = dict(zip(names, cursor.fetchone()))
        print(f"{name}: {checks[name]}", flush=True)
    result = {
        "files": profile,
        "checks": checks,
        "scope_notes": [
            "Types are inferred for exploration, not an approved source schema.",
            (
                "Source sales values are summed without changing discount treatment;"
                " revenue semantics require source documentation."
            ),
            "No raw rows were changed or deleted.",
            (
                "causal_data and coupon mapping uniqueness are not checked in this"
                " initial audit."
            ),
            (
                "Full-row transaction duplicates are observations to investigate, not"
                " an instruction to delete rows."
            ),
            "Source day numbers are retained; no calendar dates are invented.",
        ],
    }
    (REPORTS / "data_quality.json").write_text(
        json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8"
    )
    lines = [
        "# Initial source data audit",
        "",
        "Generated by `src/retail_customer_360/audit.py` from the local CSV files.",
        "",
        "| File | Rows | Size (MiB) | Null cells | Blank string cells |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, item in profile.items():
        lines.append(
            f"| {name}.csv | {item['rows']:,} | {item['bytes']/1024**2:.2f} |"
            f" {sum(c['nulls'] for c in item['columns']):,} |"
            f" {sum(c['blank_strings'] for c in item['columns']):,} |"
        )
    for name, item in checks.items():
        lines.extend(["", f"## {name}", ""])
        lines.extend(f"- {key}: {value}" for key, value in item.items())
    lines.extend(["", "## Scope and interpretation", ""])
    lines.extend("- " + note for note in result["scope_notes"])
    (REPORTS / "data_quality.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        "Reports written to reports/data_quality.md and reports/data_quality.json",
        flush=True,
    )

    con.close()


if __name__ == "__main__":
    main()
