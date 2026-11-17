"""Check code width and notebook cell length without running analysis."""
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
MAX_WIDTH = 88
MAX_CELL_LINES = 20


def main():
    failures = []
    for folder in ["src", "tests", "scripts", "sql"]:
        suffix = "*.sql" if folder == "sql" else "*.py"
        for path in (ROOT / folder).rglob(suffix):
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if len(line) > MAX_WIDTH:
                    failures.append(f"{path.name}:{number}: long line")

    for folder in ["notebooks", "additional/notebooks"]:
        for path in (ROOT / folder).glob("*.ipynb"):
            notebook = nbformat.read(path, as_version=4)
            for index, cell in enumerate(notebook.cells, 1):
                if cell.cell_type != "code":
                    continue
                lines = cell.source.splitlines()
                if len(lines) > MAX_CELL_LINES:
                    failures.append(f"{path.name}: cell {index} is too long")
                if any(len(line) > MAX_WIDTH for line in lines):
                    failures.append(f"{path.name}: cell {index} has a long line")

    if failures:
        raise SystemExit("\n".join(failures))
    print("Passed: code width <= 88; notebook code cells <= 20 lines.")


if __name__ == "__main__":
    main()
