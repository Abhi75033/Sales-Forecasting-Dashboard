from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from forecast_model import load_sales_data, train_model  # type: ignore


def main() -> None:
    df = load_sales_data()
    _ = train_model(df)
    # We retrain to keep model fresh. If persistence is desired, serialize here.
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[auto_refresh] Model retrained at {stamp} on {len(df)} rows")


if __name__ == "__main__":
    main()

import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(ROOT, "backend")
DATA_CSV = os.path.join(ROOT, "data", "sales_data.csv")

sys.path.append(BACKEND_DIR)
from forecast_model import load_sales_data, train_model, save_model  # noqa: E402


def main() -> None:
	# Retrain model from the canonical CSV and save it
	train_df = load_sales_data(DATA_CSV)
	model = train_model(train_df)
	save_model(model)
	print("Model retrained and saved.")


if __name__ == "__main__":
	main()


