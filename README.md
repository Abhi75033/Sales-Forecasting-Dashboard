Sales Forecasting Dashboard

A full-stack dashboard to forecast product sales using Prophet and visualize results with Plotly Dash. Includes a Flask REST API and a cron-friendly retraining script.

Features:
- Upload CSV (flexible headers for date and sales) and forecast next 30 days
- Plotly Dash interactive chart (actuals, forecast, confidence interval)
- Flask API `/predict` returns forecast JSON (GET uses sample, POST accepts CSV)
- "Demo" button loads sample data without uploading
- Cron script retrains the model daily

Setup:
1) python3 -m venv venv
2) source venv/bin/activate  (Windows: venv\\Scripts\\activate)
3) pip install -r requirements.txt

Run:
- Backend: cd backend && python app.py  # http://localhost:5000
- Dashboard: cd ../dashboard && python app.py  # http://localhost:8050
- Cron retrain: cd ../cron_jobs && python auto_refresh.py

API:
- GET `/` – API info
- GET `/health` – health check
- GET `/predict?periods=30` – forecast using sample data
- POST `/predict` – forecast from uploaded CSV with body: {"csv": "date,sales\n2024-01-01,100\n..."}

Accepted Header Variants:
- Date: `date`, `ds`, `order_date`, `day`, `timestamp`
- Sales: `sales`, `y`, `weekly_sales`, `revenue`, `amount`, `value`

Notes:
- Dates parsed with pandas.to_datetime, sales coerced to numeric (invalid rows dropped)

Cron / Scheduler:
- Example crontab (daily at 2am):
  0 2 * * * /path/to/venv/bin/python /path/to/project/cron_jobs/auto_refresh.py >> /path/to/log.txt 2>&1

Troubleshooting:
- Dash 2.x uses app.run(...), not app.run_server(...)
- Prophet install issues on macOS may require Xcode tools and a working cmdstan toolchain
