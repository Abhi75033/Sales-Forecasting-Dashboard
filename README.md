# 📊 Sales Forecasting Dashboard

A comprehensive full-stack web application for forecasting product sales using Facebook's Prophet time-series algorithm, featuring an interactive Plotly Dash dashboard and a RESTful Flask API.

## 🌟 Features

### Interactive Dashboard
- **Drag-and-Drop CSV Upload**: Easy data ingestion with flexible column name support
- **Demo Mode**: Instantly explore sample data without file uploads
- **Interactive Charts**: 
  - Time-series forecast visualization with confidence intervals
  - Pie charts for sales distribution by month or weekday
  - Range slider and date range filters
  - Hover tooltips with detailed information
- **KPI Cards**: Key metrics including total sales, average sales, and last data point
- **Smooth Visualizations**: 4-week rolling average for cleaner actuals display

### RESTful API
- **GET `/predict`**: Generate forecasts using sample data
- **POST `/predict`**: Upload custom CSV data for forecasting
- **Flexible Periods**: Configure forecast horizon (default: 30 days)
- **Health Check**: Monitor API status with `/health` endpoint

### Smart Data Processing
- **Flexible Headers**: Supports multiple date and sales column name variants
- Date: `date`, `ds`, `order_date`, `day`, `timestamp`
- Sales: `sales`, `y`, `weekly_sales`, `revenue`, `amount`, `value`
- **Auto-cleaning**: Handles missing values and invalid data gracefully
- **Date Parsing**: Robust datetime handling across formats

### Automated Retraining
- **Cron Script**: Daily model retraining with `auto_refresh.py`
- **Fresh Forecasts**: Always up-to-date predictions

## 🏗️ Tech Stack

- **Frontend**: [Plotly Dash](https://dash.plotly.com/) - Interactive web dashboards
- **Backend**: [Flask](https://flask.palletsprojects.com/) - RESTful API
- **Forecasting**: [Facebook Prophet](https://facebook.github.io/prophet/) - Time-series forecasting
- **Data Processing**: [Pandas](https://pandas.pydata.org/) - Data manipulation
- **Visualization**: [Plotly](https://plotly.com/python/) - Interactive charts
- **Deployment**: [Gunicorn](https://gunicorn.org/) - Production WSGI server

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd Sales_Forecasting_Dashboard
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

### Running the Application

#### Option 1: Run Dashboard Only
```bash
cd dashboard
python app.py
```
Visit `http://localhost:8050` in your browser

#### Option 2: Run Backend API Only
```bash
cd backend
python app.py
```
API available at `http://localhost:5000`

#### Option 3: Run Both Services
Open two terminal windows:
- Terminal 1: Backend
  ```bash
  cd backend && python app.py
  ```
- Terminal 2: Dashboard
  ```bash
  cd dashboard && python app.py
  ```

#### Automated Model Retraining
```bash
cd cron_jobs
python auto_refresh.py
```

For scheduled daily retraining, add to crontab:
```bash
  0 2 * * * /path/to/venv/bin/python /path/to/project/cron_jobs/auto_refresh.py >> /path/to/log.txt 2>&1
```

## 📖 API Documentation

### Base URL
```
http://localhost:5000
```

### Endpoints

#### `GET /`
Get API information and available endpoints.

**Response:**
```json
{
  "message": "Welcome to the Sales Forecasting API!",
  "endpoints": {
    "/health": "GET - Check API health",
    "/predict": "GET - Get 30-day forecast using default data",
    "/predict (POST)": "POST - Upload CSV data for forecasting"
  }
}
```

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

#### `GET /predict`
Generate forecast using sample data.

**Query Parameters:**
- `periods` (optional): Number of forecast periods (default: 30)

**Example:**
```bash
curl "http://localhost:5000/predict?periods=60"
```

**Response:**
```json
{
  "periods": 60,
  "forecast": [
    {
      "ds": "2024-12-01",
      "yhat": 250.5,
      "yhat_lower": 220.3,
      "yhat_upper": 280.7
    },
    ...
  ]
}
```

#### `POST /predict`
Generate forecast from custom CSV data.

**Request Body:**
```json
{
  "csv": "date,sales\n2024-01-01,100\n2024-01-02,120\n..."
}
```

**Query Parameters:**
- `periods` (optional): Number of forecast periods (default: 30)

**Example:**
```bash
curl -X POST "http://localhost:5000/predict?periods=30" \
  -H "Content-Type: application/json" \
  -d '{"csv": "date,sales\n2024-01-01,100\n2024-01-02,120"}'
```

**Response:**
```json
{
  "periods": 30,
  "forecast": [...]
}
```

## 📁 Project Structure

```
Sales_Forecasting_Dashboard/
├── backend/                 # Flask API backend
│   ├── app.py              # API routes and handlers
│   ├── forecast_model.py   # Prophet model logic
│   ├── models/             # Saved model files
│   └── Procfile            # Deployment configuration
├── dashboard/              # Dash frontend application
│   ├── app.py              # Dashboard layout and callbacks
│   ├── assets/
│   │   └── styles.css      # Custom styling
│   └── Procfile            # Deployment configuration
├── data/                   # Sample and uploaded data
│   └── sales_data.csv      # Demo dataset
├── cron_jobs/              # Automated tasks
│   └── auto_refresh.py     # Daily model retraining script
├── requirements.txt        # Python dependencies
├── render.yaml             # Render.com deployment config
└── README.md               # This file
```

## 📝 CSV Format

Your CSV file must contain date and sales columns. Supported column name variants:

**Date Columns:** `date`, `ds`, `order_date`, `day`, `timestamp`  
**Sales Columns:** `sales`, `y`, `weekly_sales`, `revenue`, `amount`, `value`

**Example:**
```csv
date,sales
2024-01-01,120
2024-01-02,130
2024-01-03,128
...
```

**Alternative formats also work:**
```csv
order_date,revenue
2024-01-01,120
...
```

```csv
ds,y
2024-01-01,120
...
```

## 🎯 How It Works

1. **Data Ingestion**: CSV files are processed and normalized to Prophet's expected format (`ds` for dates, `y` for values)

2. **Model Training**: Facebook Prophet is used to:
   - Detect seasonal patterns (daily, weekly, yearly)
   - Handle holidays and special events
   - Account for trends and irregularities

3. **Forecast Generation**: The trained model predicts future values with confidence intervals

4. **Visualization**: Interactive charts display:
   - Historical actuals with smoothing
   - Forecasted values
   - Uncertainty bands
   - Sales distribution patterns

## 🚢 Deployment

### Render.com

The project includes `render.yaml` for easy deployment to Render.com:

```yaml
services:
  - type: web
    name: sales-forecasting-backend
    ...
  - type: web
    name: sales-forecasting-dashboard
    ...
```

Deploy with a single click after connecting your GitHub repository.

### Other Platforms

The application can be deployed to any platform supporting Python:
- Heroku
- AWS Elastic Beanstalk
- Google Cloud Run
- Azure App Service
- DigitalOcean App Platform

Ensure environment variables are set:
- `PORT`: Application port (set by platform)
- `PYTHONUNBUFFERED`: Set to `1` for proper logging

## 🔧 Troubleshooting

### Prophet Installation Issues
If you encounter Prophet installation problems on macOS:
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Ensure cmdstan is properly installed
pip install cmdstanpy
python -c "import cmdstanpy; cmdstanpy.install_cmdstan()"
```

### Dash Import Errors
Make sure you're using Dash 2.x syntax:
```python
app.run(debug=True)  # Correct for Dash 2.x
# NOT app.run_server(debug=True)  # Old Dash 1.x syntax
```

### Port Conflicts
If port 5000 or 8050 is already in use:
```bash
# Find and kill the process
lsof -ti:5000 | xargs kill -9
lsof -ti:8050 | xargs kill -9
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- [Facebook Prophet](https://facebook.github.io/prophet/) - Time-series forecasting library
- [Plotly](https://plotly.com/python/) - Interactive visualization library
- [Dash](https://dash.plotly.com/) - Python framework for building web applications

## 📞 Support

For questions, issues, or feature requests, please open an issue on the GitHub repository.

---

**Happy Forecasting! 📈**
