from __future__ import annotations

import os
from io import StringIO
from typing import Any, List

from flask import Flask, jsonify, request
import pandas as pd

from pathlib import Path

from forecast_model import (
    ensure_model,
    forecast,
    forecast_to_json,
    load_sales_data,
)


app = Flask(__name__)


@app.route("/", methods=["GET"])
def index() -> Any:
    return jsonify({
        "message": "Welcome to the Sales Forecasting API!",
        "endpoints": {
            "/health": "GET - Check API health",
            "/predict": "GET - Get 30-day forecast using default data (e.g., /predict?periods=60)",
            "/predict (POST)": "POST - Upload CSV data for forecasting (JSON body: {'csv': 'date,sales\\n2023-01-01,100\\n...'})"
        }
    })


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify({"status": "ok"})


def _normalize_uploaded_csv_to_df(csv_text: str) -> pd.DataFrame:
    df_raw = pd.read_csv(StringIO(csv_text))
    # Normalize columns for flexibility
    df_raw.columns = df_raw.columns.str.strip().str.lower()
    date_candidates = ["date", "ds", "order_date", "day", "timestamp"]
    sales_candidates = ["sales", "y", "weekly_sales", "revenue", "amount", "value"]

    date_col = next((col for col in df_raw.columns if col in date_candidates), None)
    sales_col = next((col for col in df_raw.columns if col in sales_candidates), None)

    if not date_col or not sales_col:
        found_cols = df_raw.columns.tolist()
        return pd.DataFrame(), f"CSV must contain a Date (one of {date_candidates}) and Sales (one of {sales_candidates}) columns. Found: {found_cols}"

    df_raw = df_raw.rename(columns={date_col: "ds", sales_col: "y"})
    df_raw["ds"] = pd.to_datetime(df_raw["ds"], errors="coerce")
    df_raw["y"] = pd.to_numeric(df_raw["y"], errors="coerce")
    df_raw.dropna(subset=["ds", "y"], inplace=True)
    if df_raw.empty:
        return pd.DataFrame(), "No valid rows after parsing. Ensure dates and numeric sales values."
    return df_raw[["ds", "y"]].sort_values("ds").reset_index(drop=True), None


@app.route("/predict", methods=["GET", "POST"])
def predict() -> Any:
    try:
        periods = int(request.args.get("periods", 30))
        if periods <= 0:
            return jsonify({"error": "periods must be > 0"}), 400
    except Exception:
        return jsonify({"error": "Invalid periods parameter"}), 400

    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            csv_text = data.get("csv")
            if not csv_text:
                return jsonify({"error": "Missing 'csv' in JSON body"}), 400

            df, err = _normalize_uploaded_csv_to_df(csv_text)
            if err:
                return jsonify({"error": err}), 400

            model = ensure_model(data_path=None)  # model structure; we will fit on df instead
            # Train directly on provided df
            from forecast_model import train_model

            model = train_model(df)
            fcst_df = forecast(model, periods=periods, last_date=df["ds"].max())
        else:  # GET -> use default sample data
            df = load_sales_data()
            model = ensure_model()
            fcst_df = forecast(model, periods=periods, last_date=df["ds"].max())

        return jsonify({
            "periods": periods,
            "forecast": forecast_to_json(fcst_df)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

import os
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS

from forecast_model import ensure_model, forecast, forecast_to_json, load_sales_data, save_model, train_model


app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def index() -> Any:
	return jsonify({
		"message": "Sales Forecasting API",
		"endpoints": {
			"health": "/health",
			"predict_get": "/predict?periods=30",
			"predict_post": {
				"path": "/predict",
				"body": {"csv": "Date,Sales\n2025-10-01,100\n..."}
			}
		}
	})


@app.route("/health", methods=["GET"])
def health() -> Any:
	return jsonify({"status": "ok"})


@app.route("/predict", methods=["GET", "POST"])
def predict() -> Any:
	"""
	Returns forecast JSON for next N days.

	- GET: reads from default data CSV and uses saved model (or trains if missing)
	- POST: accepts uploaded CSV content in JSON body under key 'csv' (string)
	"""
	periods = int(request.args.get("periods", "30"))

	# Accept optional CSV via POST
	if request.method == "POST":
		payload: Dict[str, Any] = request.get_json(silent=True) or {}
		csv_text = payload.get("csv")
		if csv_text:
			from io import StringIO
			import pandas as pd

			df_raw = pd.read_csv(StringIO(csv_text))
			# Normalize columns (case/whitespace) and support aliases
			lower_map = {c.strip().lower(): c for c in df_raw.columns}
			date_col = lower_map.get("date") or lower_map.get("ds")
			sales_col = lower_map.get("sales") or lower_map.get("y")
			if not date_col or not sales_col:
				return jsonify({
					"error": "CSV must contain 'Date' (or 'ds') and 'Sales' (or 'y') columns",
					"found_columns": list(df_raw.columns)
				}), 400
			df_raw = df_raw.rename(columns={date_col: "ds", sales_col: "y"})
			df_raw["ds"] = pd.to_datetime(df_raw["ds"])  # type: ignore[assignment]
			df_raw["y"] = pd.to_numeric(df_raw["y"], errors='coerce')  # type: ignore[assignment]
			df_raw = df_raw.dropna(subset=["ds", "y"]).copy()
			model = train_model(df_raw[["ds", "y"]].sort_values("ds").reset_index(drop=True))
			fcst_df = forecast(model, periods=periods)
			return app.response_class(forecast_to_json(fcst_df), mimetype="application/json")

	# Fallback to saved model and default CSV
	model, train_df = ensure_model()
	fcst_df = forecast(model, periods=periods)
	return app.response_class(forecast_to_json(fcst_df), mimetype="application/json")


if __name__ == "__main__":
	port = int(os.environ.get("PORT", "5000"))
	app.run(host="0.0.0.0", port=port, debug=True)


