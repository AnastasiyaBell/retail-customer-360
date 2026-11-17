# Reading the notebooks

Python and SQL code lines are limited to 88 characters. Notebook code is grouped into short logical steps, normally no more than 16-20 lines. Markdown step labels separate loading, intermediate inspection, calculation, checking and plotting. A query or control-flow block remains together when required for valid Python.

Loaded/derived tables have read-only previews where useful. Final metric tables replace dense interpolated text. Figures are displayed after their drawing steps are complete, avoiding partial charts when plotting spans cells. Display formatting does not alter eligibility, features, model selection or budget rules.

Run each notebook top-to-bottom in the project environment. Intermediate variables intentionally carry state between short cells; a later cell may require earlier setup. Saved outputs show a verified full run. Additional notebooks remain independently runnable from their nested directories.

Python formatting configuration is in pyproject.toml; optional development formatters are pinned in requirements-dev.txt. Formatting utilities are not dependencies of the analysis itself. Literal strings may use adjacent quoted pieces to fit within the width; Python concatenates them automatically.

## Figures split across cells

Use an explicit matplotlib.figure.Figure object rather than pyplot-managed automatic output. The finish helper saves and embeds the complete PNG with IPython.display.Image. This avoids displaying a half-built figure or losing a panel when later cells add its points. Only the final chart cell should contain the embedded image.
