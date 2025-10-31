from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    # prophet (new package name)
    from prophet import Prophet  # type: ignore
except Exception:  # pragma: no cover - fallback for some environments
    # fbprophet (legacy)
    from fbprophet import Prophet  # type: ignore


# ---- Paths ----
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DATA_PATH = DATA_DIR / "sales_data.csv"
MODEL_DIR = PROJECT_ROOT / "backend" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODEL_DIR / "prophet_model.pkl"


def _normalize_sales_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize incoming dataframe to Prophet's expected columns ds (date) and y (value).

    Accepts flexible header names for date and sales.
    """
    if df is None or df.empty:
        raise ValueError("Input dataframe is empty.")

    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()

    date_candidates = [
        "date",
        "ds",
        "order_date",
        "day",
        "timestamp",
    ]
    sales_candidates = [
        "sales",
        "y",
        "weekly_sales",
        "revenue",
        "amount",
        "value",
    ]

    date_col = next((c for c in df.columns if c in date_candidates), None)
    sales_col = next((c for c in df.columns if c in sales_candidates), None)

    if not date_col or not sales_col:
        raise ValueError(
            f"CSV must contain a date column (one of {date_candidates}) and a sales column (one of {sales_candidates}). Found: {df.columns.tolist()}"
        )

    df = df.rename(columns={date_col: "ds", sales_col: "y"})
    df["ds"] = pd.to_datetime(df["ds"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df = df.dropna(subset=["ds", "y"]).sort_values("ds").reset_index(drop=True)

    if df.empty:
        raise ValueError("No valid rows after cleaning. Ensure dates and numeric sales are provided.")

    return df[["ds", "y"]]


def load_sales_data(path: Optional[str | os.PathLike[str]] = None) -> pd.DataFrame:
    """Load sales data CSV and normalize it for Prophet."""
    csv_path = Path(path) if path else DEFAULT_DATA_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Sales data not found at {csv_path}")
    df = pd.read_csv(csv_path)
    return _normalize_sales_dataframe(df)


def train_model(df: pd.DataFrame) -> Prophet:
    """Train a Prophet model on the given dataframe (expects ds, y)."""
    df_norm = _normalize_sales_dataframe(df)
    model = Prophet()
    model.fit(df_norm)
    return model


def forecast(model: Prophet, periods: int, last_date: Optional[pd.Timestamp | datetime] = None) -> pd.DataFrame:
    """Generate a forecast dataframe for the specified periods beyond last_date.

    If last_date is not provided, infer from the model's training data frequency (daily) and tail date.
    """
    if periods <= 0:
        raise ValueError("periods must be > 0")

    # Prophet's make_future_dataframe works off training cutoff; we assume daily data.
    future = model.make_future_dataframe(periods=periods, freq="D")
    fcst = model.predict(future)
    return fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]]


def forecast_to_json(fcst_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Serialize forecast dataframe to JSON-serializable list of dicts."""
    result: List[Dict[str, Any]] = []
    for _, row in fcst_df.iterrows():
        result.append(
            {
                "ds": pd.to_datetime(row["ds"]).strftime("%Y-%m-%d"),
                "yhat": float(row["yhat"]),
                "yhat_lower": float(row["yhat_lower"]),
                "yhat_upper": float(row["yhat_upper"]),
            }
        )
    return result


def ensure_model(data_path: Optional[str | os.PathLike[str]] = None) -> Prophet:
    """Train a model from provided or default data and return it.

    We keep it simple and retrain rather than persisting a cache, to avoid
    environment-specific serialization issues.
    """
    df = load_sales_data(data_path)
    return train_model(df)


__all__ = [
    "load_sales_data",
    "train_model",
    "forecast",
    "forecast_to_json",
    "ensure_model",
]

import os
import json
import pickle
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd
from prophet import Prophet


MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/sales_data.csv")


def load_sales_data(csv_path: Optional[str] = None) -> pd.DataFrame:
	"""Load sales data CSV with columns Date, Sales and return Prophet-ready df with ds, y."""
	csv_to_load = csv_path or os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/sales_data.csv"))
	df = pd.read_csv(csv_to_load)
	# Normalize columns
	if "Date" in df.columns:
		df["ds"] = pd.to_datetime(df["Date"])  # type: ignore[assignment]
	else:
		raise ValueError("CSV must contain a 'Date' column")
	if "Sales" in df.columns:
		df["y"] = pd.to_numeric(df["Sales"])  # type: ignore[assignment]
	else:
		raise ValueError("CSV must contain a 'Sales' column")
	return df[["ds", "y"]].sort_values("ds").reset_index(drop=True)


def train_model(df: pd.DataFrame) -> Prophet:
	"""Train and return a Prophet model on the given dataframe."""
	model = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True)
	model.fit(df)
	return model


def save_model(model: Prophet, model_path: str = MODEL_PATH) -> None:
	with open(model_path, "wb") as f:
		pickle.dump(model, f)


def load_model(model_path: str = MODEL_PATH) -> Optional[Prophet]:
	if not os.path.exists(model_path):
		return None
	with open(model_path, "rb") as f:
		return pickle.load(f)


def ensure_model(csv_path: Optional[str] = None) -> Tuple[Prophet, pd.DataFrame]:
	"""Return a trained Prophet model and the training df. Train if missing."""
	model = load_model()
	train_df = load_sales_data(csv_path)
	if model is None:
		model = train_model(train_df)
		save_model(model)
	return model, train_df


def forecast(model: Prophet, periods: int = 30, last_date: Optional[pd.Timestamp] = None) -> pd.DataFrame:
	"""Create a forecast dataframe for the next `periods` days."""
	if last_date is None:
		last_date = model.history["ds"].max()
	future = model.make_future_dataframe(periods=periods, freq="D")
	fcst = model.predict(future)
	# Return only relevant columns
	return fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]].loc[fcst["ds"] > last_date].reset_index(drop=True)


def forecast_to_json(df: pd.DataFrame) -> str:
	"""Serialize forecast dataframe to JSON string list of objects."""
	records = [
		{
			"date": datetime.strftime(pd.to_datetime(row["ds"]).to_pydatetime(), "%Y-%m-%d"),
			"yhat": float(row["yhat"]),
			"yhat_lower": float(row["yhat_lower"]),
			"yhat_upper": float(row["yhat_upper"]),
		}
		for _, row in df.iterrows()
	]
	return json.dumps(records)


