("Run from any working directory with the project Python environment.")

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retail_customer_360.pipeline import main

if __name__ == "__main__":
    main()
