"""Benchmark notebook calculations in fresh Windows processes; verify parity."""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import nbformat
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/coupon_benchmark"
NOTEBOOKS = {
    "sql": "03_coupon_recommendation_experiment.ipynb",
    "pandas": "04_coupon_recommendation_pandas.ipynb",
}


def peak_working_set():
    """OS peak resident working set for the whole process, in MiB."""
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in [
                "peak_ws", "ws", "peak_pool", "pool", "peak_nonpool",
                "nonpool", "pagefile", "peak_pagefile",
            ]
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD
    ]
    if not psapi.GetProcessMemoryInfo(
        kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.peak_ws / 1024**2


def child(engine, trial):
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT / "src"))
    # Warm common imports before timing; no data loaded in advance.
    from retail_customer_360.metrics import load_transactions  # noqa: F401

    notebook = nbformat.read(
        ROOT / "additional/notebooks" / NOTEBOOKS[engine], as_version=4
    )
    scope = {"display": lambda *args, **kwargs: None}
    started = time.perf_counter()
    loaded = None
    for cell in notebook.cells:
        if cell.cell_type != "code" or "# Verification:" in cell.source:
            continue
        source = cell.source.replace("con.close()", "")
        exec(compile(source, NOTEBOOKS[engine], "exec"), scope)
        if '"redemptions": "coupon_redempt.csv"' in source or (
            'redemptions = read_source("coupon_redempt.csv")' in source
        ):
            loaded = time.perf_counter()
    ended = time.perf_counter()
    peak = peak_working_set()
    if engine == "sql":
        evaluated = scope["con"].execute("SELECT * FROM evaluated").df()
        scope["con"].close()
    else:
        evaluated = scope["evaluated"]
    evaluated.columns = evaluated.columns.str.lower()
    # Parity extraction/export is outside the measured interval and peak sample.
    evaluated.to_pickle(OUT / f"{engine}_candidates.pkl")
    result = {
        "engine": engine, "trial": trial,
        "load_seconds": loaded - started,
        "analysis_seconds": ended - loaded,
        "total_seconds": ended - started,
        "peak_working_set_mib": peak,
    }
    (OUT / f"{engine}_{trial}.json").write_text(json.dumps(result))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for trial in range(1, 4):
        order = ["sql", "pandas"] if trial % 2 else ["pandas", "sql"]
        for engine in order:
            subprocess.run(
                [sys.executable, str(Path(__file__)), engine, str(trial)],
                cwd=ROOT, check=True,
            )
            result = json.loads((OUT / f"{engine}_{trial}.json").read_text())
            rows.append(result)
            print(json.dumps(result), flush=True)
    keys = ["campaign", "household_key", "coupon_upc"]
    left = pd.read_pickle(OUT / "sql_candidates.pkl")
    right = pd.read_pickle(OUT / "pandas_candidates.pkl")
    left = left.sort_values(keys).reset_index(drop=True)
    right = right[left.columns].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right, check_dtype=False, check_exact=True)
    pd.DataFrame(rows).to_csv(OUT / "timings.csv", index=False)
    metadata = {
        "python": sys.version, "platform": platform.platform(),
        "pandas": pd.__version__, "numpy": np.__version__,
        "candidate_rows_exactly_equal": len(left),
    }
    (OUT / "environment.json").write_text(json.dumps(metadata, indent=2))
    print(f"Exact parity: {len(left):,} candidate rows, all columns.")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        child(sys.argv[1], int(sys.argv[2]))
    else:
        main()
