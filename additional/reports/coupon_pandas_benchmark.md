# SQL and Pandas coupon notebook benchmark

Both notebooks implement the same historical recommendation rules. The main
USD 2 audience-selection scenario is unchanged.

## Measured results

| Engine | Load/validate CSV, s | Analysis/export, s | Total, s | Peak RAM, MiB |
|---|---:|---:|---:|---:|
| pandas | 6.54 | 3.54 | 9.17 | 675 |
| sql | 1.44 | 2.29 | 3.71 | 1063 |

Medians of three fresh-process runs per engine. Pandas/SQL total-time ratio: **2.47x** on this machine.

Peak RAM is the Windows process peak working set, including interpreter,
libraries and intermediates. It is sampled before candidate-parity extraction;
the OS retains the historical peak. It is not total allocated or virtual memory.

## Reproduce

```powershell
.venv/Scripts/python.exe scripts/benchmark_coupon_notebooks.py
```

- Each run executes notebook code in a new Python process. Notebook parsing
  and common library imports are completed before the clock starts.
- Timing includes CSV reading, monetary validation, calculations, assertions
  and the four normal CSV exports. Display is disabled. Kernel startup,
  rendering, cross-implementation checks and parity exports are excluded.
- Loading ends after all five CSVs are read; analysis includes paid-basket
  filtering, all 24 campaign decisions, ranking, future labels and metrics.
- Both loaders initially read all transaction fields as strings and enforce
  the same monetary policy. Pandas uses numeric sales only for eligibility;
  SQL retains validated DECIMAL cents. No monetary sums are used here.
- Trial order alternates SQL/Pandas, Pandas/SQL, SQL/Pandas. The OS file cache
  is not cleared; these are repeated-run timings, not controlled cold-disk tests.
- DuckDB retains the project 1 GB memory setting and two threads. Pandas
  processes campaigns sequentially, bounding intermediate join sizes.
- The implementations and execution strategies differ. These figures are
  evidence for these notebooks on this machine, not a universal engine ranking.

First runs were slower for both implementations. Total times across
the three trials were SQL 7.92 / 3.71 / 3.67 s and Pandas
19.14 / 9.17 / 7.91 s. This variation limits precision of any speed ratio.

## Result agreement

The benchmark compares every candidate column exactly after normalising column
case, sorting stable keys and ignoring storage dtypes. This includes personal
scores, popularity, both ranks and both future outcome labels: all
**53,417 candidate rows match exactly**.
The Pandas notebook also compares all four reference CSV exports. Integer
values agree exactly; aggregated floating metrics use tolerance 1e-12 because
sum/mean order can change the final binary digits.

Full trials, machine/package metadata and candidate snapshots are local under
`data/processed/coupon_benchmark/`, excluded from Git.

## Interpretation

Pandas is usable at this dataset size. Choose based on readability and
resource needs; moving campaign processing into large unbounded merges could
change both speed and memory substantially. Recommendation relevance still
does not measure coupon uplift, incremental profit or optimal discount value.
