# Local manual refresh; no scheduled task, upload or customer messaging.
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create the project .venv first.' }
& $pythonPath (Join-Path $PSScriptRoot 'run_pipeline.py') @args
if ($LASTEXITCODE -ne 0) { throw "Pipeline failed with exit code $LASTEXITCODE" }
