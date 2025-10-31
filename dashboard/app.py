from __future__ import annotations

import base64
import os
from io import StringIO
from pathlib import Path
from typing import Any, Optional

import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.graph_objects as go
import calendar

# Allow importing backend utilities
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.append(str(PROJECT_ROOT / "backend"))

from forecast_model import train_model, forecast  # type: ignore


app: Dash = dash.Dash(__name__)
app.title = "Sales Forecasting Dashboard"
server = app.server


def parse_contents(contents: str | pd.DataFrame) -> pd.DataFrame:
    if isinstance(contents, pd.DataFrame):
        df = contents
    else:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(StringIO(decoded.decode('utf-8')))

    # Normalize column names for flexibility
    df.columns = df.columns.str.strip().str.lower()
    date_candidates = ["date", "ds", "order_date", "day", "timestamp"]
    sales_candidates = ["sales", "y", "weekly_sales", "revenue", "amount", "value"]

    date_col = next((col for col in df.columns if col in date_candidates), None)
    sales_col = next((col for col in df.columns if col in sales_candidates), None)

    if not date_col or not sales_col:
        found_cols = df.columns.tolist()
        raise ValueError(
            f"CSV must contain 'Date' (one of {date_candidates}) and 'Sales' (one of {sales_candidates}). Found: {found_cols}"
        )

    df = df.rename(columns={date_col: "ds", sales_col: "y"})
    df["ds"] = pd.to_datetime(df["ds"], errors='coerce')
    df["y"] = pd.to_numeric(df["y"], errors='coerce')
    df.dropna(subset=["ds", "y"], inplace=True)

    if df.empty:
        raise ValueError("No valid numeric sales data found after processing.")

    return df[["ds", "y"]].sort_values("ds").reset_index(drop=True)


app.layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Sales Forecasting Dashboard", className="app-title"),
            html.P("Upload a CSV to forecast the next 30 days or click Demo to explore sample data.", className="app-subtitle"),
        ], className="header-text"),
    ], className="app-header"),

    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
            className="upload-area",
            multiple=False
        ),
        html.Button('Demo', id='demo-btn', n_clicks=0, className="btn btn-primary"),
        html.Div([
            html.Label("Pie Chart Dimension:"),
            dcc.RadioItems(
                id='pie-dim',
                options=[
                    {'label': 'Month', 'value': 'month'},
                    {'label': 'Weekday', 'value': 'weekday'},
                ],
                value='month',
                className="radio-inline"
            ),
        ], className="controls-right"),
    ], className="toolbar"),

    html.Div(id='output-graphs', children="Awaiting CSV upload or click Demo...", className="content")
], className="container")


@app.callback(Output('output-graphs', 'children'),
              [Input('upload-data', 'contents'),
               Input('demo-btn', 'n_clicks'),
               Input('pie-dim', 'value')],
              [State('upload-data', 'filename')])
def update_output(contents, n_clicks, pie_dim, filename):
    ctx = dash.callback_context
    if not ctx.triggered:
        return html.Div("Awaiting CSV upload or click Demo...")

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    df = None
    title = "Sales Forecast"

    if trigger_id == 'upload-data' and contents:
        try:
            df = parse_contents(contents)
            title = filename if filename else "Uploaded Sales Data"
        except ValueError as e:
            return html.Div(f"Error processing file: {e}")
        except Exception as e:
            return html.Div(f"An unexpected error occurred during file processing: {e}")
    elif trigger_id == 'demo-btn' and n_clicks > 0:
        try:
            data_path = PROJECT_ROOT / "data" / "sales_data.csv"
            df = pd.read_csv(data_path)
            # Pass the DataFrame directly to reuse normalization logic
            df = parse_contents(df)
            title = "Demo Sales Data (sales_data.csv)"
        except Exception as e:
            return html.Div(f"Error loading demo data: {e}")
    else:
        return html.Div("Awaiting CSV upload or click Demo...")

    if df is None or df.empty:
        return html.Div("No data to display. Please upload a valid CSV or try the Demo.")

    try:
        model = train_model(df)
        fcst_df = forecast(model, periods=30, last_date=df["ds"].max())

        # Rolling average to smooth noisy actuals (4-week window)
        df_sorted = df.sort_values("ds").reset_index(drop=True)
        df_sorted["y_ma"] = df_sorted["y"].rolling(window=4, min_periods=1).mean()

        fig = go.Figure()

        # Confidence interval band (subtle fill)
        fig.add_trace(
            go.Scatter(
                x=fcst_df["ds"],
                y=fcst_df["yhat_upper"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=fcst_df["ds"],
                y=fcst_df["yhat_lower"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(255,127,14,0.15)",
                name="Confidence Interval",
                hoverinfo="skip",
            )
        )

        # Forecast line
        fig.add_trace(
            go.Scatter(
                x=fcst_df["ds"],
                y=fcst_df["yhat"],
                mode="lines",
                name="Forecast",
                line=dict(color="#ff7f0e", width=2),
                hovertemplate="%{x|%b %d, %Y}<br>Forecast: %{y:,.0f}<extra></extra>",
            )
        )

        # Actuals (thin line) and smoothed average (thicker)
        fig.add_trace(
            go.Scatter(
                x=df_sorted["ds"],
                y=df_sorted["y"],
                mode="lines",
                name="Actual Sales",
                line=dict(color="#1f77b4", width=1),
                opacity=0.4,
                hovertemplate="%{x|%b %d, %Y}<br>Actual: %{y:,.0f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df_sorted["ds"],
                y=df_sorted["y_ma"],
                mode="lines",
                name="Actual (4-Week Avg)",
                line=dict(color="#1f77b4", width=2.5),
                hovertemplate="%{x|%b %d, %Y}<br>Actual (Avg): %{y:,.0f}<extra></extra>",
            )
        )

        fig.update_layout(
            title=f"{title} Forecast (Next 30 Days)",
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=40, r=20, t=60, b=40),
            xaxis=dict(
                title="Date",
                rangeslider=dict(visible=True),
                rangeselector=dict(
                    buttons=[
                        dict(count=6, label="6M", step="month", stepmode="backward"),
                        dict(count=1, label="1Y", step="year", stepmode="backward"),
                        dict(step="all", label="All"),
                    ]
                ),
            ),
            yaxis=dict(title="Sales", separatethousands=True),
        )

        # Build pie chart: sales distribution by month or weekday
        if pie_dim == 'weekday':
            df_sorted['weekday_num'] = df_sorted['ds'].dt.weekday  # 0=Mon
            df_sorted['weekday'] = df_sorted['ds'].dt.day_name().str[:3]
            order = list(range(7))
            agg = df_sorted.groupby('weekday_num', as_index=False)['y'].sum().sort_values('weekday_num')
            labels = [calendar.day_abbr[i] for i in agg['weekday_num']]
            values = agg['y']
            pie_title = 'Sales Distribution by Weekday'
        else:
            df_sorted['month_num'] = df_sorted['ds'].dt.month
            agg = df_sorted.groupby('month_num', as_index=False)['y'].sum().sort_values('month_num')
            labels = [calendar.month_abbr[i] for i in agg['month_num']]
            values = agg['y']
            pie_title = 'Sales Distribution by Month'

        pie_fig = go.Figure(
            data=[go.Pie(labels=labels, values=values, hole=0.45, sort=False)],
        )
        pie_fig.update_traces(textinfo='percent+label', hovertemplate="%{label}: %{value:,.0f} (%{percent})<extra></extra>")
        pie_fig.update_layout(title=pie_title, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0))

        # KPI cards
        total_sales = float(df_sorted['y'].sum())
        avg_sales = float(df_sorted['y'].mean())
        last_date = df_sorted['ds'].max().strftime('%b %d, %Y')

        kpis = html.Div([
            html.Div([
                html.Div("Total Sales", className="kpi-label"),
                html.Div(f"{total_sales:,.0f}", className="kpi-value"),
            ], className="kpi-card"),
            html.Div([
                html.Div("Average Sales", className="kpi-label"),
                html.Div(f"{avg_sales:,.0f}", className="kpi-value"),
            ], className="kpi-card"),
            html.Div([
                html.Div("Last Date", className="kpi-label"),
                html.Div(last_date, className="kpi-value"),
            ], className="kpi-card"),
        ], className="kpi-grid")

        tabs = dcc.Tabs([
            dcc.Tab(label="Forecast", children=[
                dcc.Graph(figure=fig, config={"displayModeBar": True}),
            ]),
            dcc.Tab(label="Distribution", children=[
                dcc.Graph(figure=pie_fig, config={"displayModeBar": True}),
            ]),
        ])

        return html.Div([
            html.H3(title, className="section-title"),
            kpis,
            tabs,
        ], className="panel")
    except Exception as e:
        return html.Div(f"Error generating forecast: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)

import os
from datetime import datetime
from io import StringIO

import pandas as pd
import plotly.graph_objs as go
from dash import Dash, dcc, html, Input, Output, State

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from forecast_model import train_model, forecast  # noqa: E402


external_stylesheets = [
	os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "styles.css"))
]

app = Dash(__name__)
server = app.server

app.title = "Sales Forecasting Dashboard"


def parse_contents(contents: str) -> pd.DataFrame:
	content_type, content_string = contents.split(',')
	import base64
	decoded = base64.b64decode(content_string)
	df = pd.read_csv(StringIO(decoded.decode('utf-8')))
	# Normalize headers (case/whitespace) and support aliases
	lower_map = {c.strip().lower(): c for c in df.columns}
	date_col = lower_map.get("date") or lower_map.get("ds")
	sales_col = lower_map.get("sales") or lower_map.get("y")
	if not date_col or not sales_col:
		raise ValueError(f"CSV must contain 'Date' (or 'ds') and 'Sales' (or 'y') columns. Found: {list(df.columns)}")
	df = df.rename(columns={date_col: "ds", sales_col: "y"})
	df["ds"] = pd.to_datetime(df["ds"])  # type: ignore[assignment]
	df["y"] = pd.to_numeric(df["y"], errors='coerce')  # type: ignore[assignment]
	df = df.dropna(subset=["ds", "y"]).copy()
	return df[["ds", "y"]].sort_values("ds").reset_index(drop=True)


app.layout = html.Div([
	html.H1("Sales Forecasting Dashboard"),
	html.P("Upload a CSV with columns Date, Sales to generate a 30-day forecast."),
	dcc.Upload(
		id='upload-data',
		children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
		style={'width': '100%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '1px',
			   'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px'},
		multiple=False
	),
	html.Button('Demo', id='demo-btn', n_clicks=0, style={'margin': '8px 0'}),
	html.Div(id='output-graphs')
])


@app.callback(Output('output-graphs', 'children'),
			[Input('upload-data', 'contents'), Input('demo-btn', 'n_clicks')],
			[State('upload-data', 'filename')])
def update_output(contents, demo_clicks, filename):  # type: ignore[override]
	try:
		if contents is not None:
			df = parse_contents(contents)
			display_name = filename or "Uploaded CSV"
		else:
			# Demo mode when demo button clicked
			if not demo_clicks:
				return html.Div("Awaiting CSV upload or click Demo...")
			demo_csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sales_data.csv"))
			df_raw = pd.read_csv(demo_csv_path)
			lower_map = {c.strip().lower(): c for c in df_raw.columns}
			date_col = lower_map.get("date") or lower_map.get("ds")
			sales_col = lower_map.get("sales") or lower_map.get("y")
			if not date_col or not sales_col:
				raise ValueError(f"Demo CSV must contain 'Date' (or 'ds') and 'Sales' (or 'y') columns. Found: {list(df_raw.columns)}")
			df = df_raw.rename(columns={date_col: "ds", sales_col: "y"})
			df["ds"] = pd.to_datetime(df["ds"])  # type: ignore[assignment]
			df["y"] = pd.to_numeric(df["y"], errors='coerce')  # type: ignore[assignment]
			df = df[["ds", "y"]].sort_values("ds").reset_index(drop=True)
			display_name = "Demo: sales_data.csv"

		model = train_model(df)
		fcst_df = forecast(model, periods=30, last_date=df["ds"].max())
		fig = go.Figure()
		fig.add_trace(go.Scatter(x=df["ds"], y=df["y"], mode='lines+markers', name='Actual Sales'))
		fig.add_trace(go.Scatter(x=fcst_df["ds"], y=fcst_df["yhat"], mode='lines', name='Forecast'))
		fig.add_trace(go.Scatter(x=fcst_df["ds"], y=fcst_df["yhat_upper"], mode='lines', line=dict(width=0), showlegend=False))
		fig.add_trace(go.Scatter(x=fcst_df["ds"], y=fcst_df["yhat_lower"], mode='lines', fill='tonexty', line=dict(width=0), name='Confidence Interval'))
		fig.update_layout(title='Sales Forecast (Next 30 Days)', xaxis_title='Date', yaxis_title='Sales')
		return html.Div([
			html.H3(display_name),
			dcc.Graph(figure=fig)
		])
	except Exception as e:  # noqa: BLE001
		return html.Div(f"Error processing file: {e}")


if __name__ == '__main__':
	port = int(os.environ.get("DASH_PORT", "8050"))
	app.run(host='0.0.0.0', port=port, debug=True)


