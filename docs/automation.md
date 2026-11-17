# Technical refresh: main and supplementary outputs

This command continues to refresh the broad technical export package, including optional cohorts/clusters/value tables. The main reading path is shortened in README; the script is not a household-coupon recommender. Optional analysis lives in additional/.

## One-command execution

Use Python 3.12 and the pinned environment described in reproduce.md. From the project root:

```powershell
.venv/Scripts/python.exe scripts/run_pipeline.py
```

Or use the wrapper:

```powershell
./scripts/refresh.ps1
```

Optional historical cutoff (overwrites snapshots; rerun default afterward to restore the full-data snapshot):

```powershell
.venv/Scripts/python.exe scripts/run_pipeline.py --as-of-day 690
```

Custom assumptions:

```powershell
.venv/Scripts/python.exe scripts/run_pipeline.py --config config/project.json
```

The current feature contract fixes lookback=180 and label horizon=30. The rolling evaluation requires at least 660 source days; do not silently create future data to meet this requirement. Cutoff defaults to the latest observed source day, not the current calendar date. New input data must follow the documented schema and quality rules. Raw sources are not downloaded or altered automatically.

## What the command does

1. Read/validate source sales precision and basket consistency; refresh existing descriptive metrics.
2. Compute cutoff-aware features, RFM, K-Means, cohorts, retention and assumption-based contribution value.
3. Build chronological labelled snapshots, compare baselines/models, freeze evaluation, then fit the chosen deployment architecture on completed labels.
4. Score eligible latest households and select a positive-value CRM scenario audience within worst-case budget.
5. Write private relational BI datasets and aggregate public-candidate datasets.
6. Save model artefacts, parameter snapshots, source SHA-256 hashes and evaluation metadata.

Core outputs: `data/processed/portfolio/household_snapshot.csv`, `crm_targets.csv`, `crm_summary.json`, `model_manifest.json`, `run_manifest.json`, `models/`, `bi_private/`, `bi_public/`. All are Git-ignored. The original notebook-02 metric exports under data/processed are refreshed as well. Exports are replaced on rerun; a failed run must be rerun successfully before using mixed intermediate files. A complete run_manifest is written only after all stages succeed.

The analytical pipeline generates numeric datasets and models. It does **not** regenerate notebook outputs or Markdown narrative reports automatically. Rerun the relevant main notebooks and, when needed, the independent additional notebooks; update summaries after changing data/config. Their saved outputs and the reports are explicit snapshots; notebook 06 checks source hashes and config against the successful pipeline manifest before recomputing CRM scenarios.

## Optional scheduling, not installed

For a genuinely changing dataset, create a Windows Task Scheduler task manually: program = absolute `.venv/Scripts/python.exe`; arguments = absolute `scripts/run_pipeline.py`; Start in = repository root. Choose an appropriate cadence after deciding how upstream files arrive. Capture exit status/logs and validate the successful manifest before downstream use. No scheduled task or background service has been installed by this project.

## Optional Databricks migration, not executed

- Store approved raw inputs in governed cloud/Unity Catalog locations and declare schemas instead of inferring everything on each refresh.
- Port receipt and feature SQL to Spark SQL/Delta tables, validating engine-specific temporary-table, FILTER and date/index semantics.
- Partition large transaction/promotional processing upstream; keep the small household feature table for scikit-learn or a validated Spark implementation.
- Track model/evaluation/config artefacts with an approved experiment system and schedule a workflow only after parity checks against local outputs.
- Preserve chronological label boundaries and publish no household extracts by default.

No cloud workspace, cluster, upload, deployment or Databricks execution is claimed.
