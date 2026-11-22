# Koshflow (ATM Cash Demand Predictor)

**AI-powered ATM cash demand forecasting and smart replenishment route optimization to eliminate cash-out incidents and minimize cash transit costs.**

---

## 🎯 Model Metrics

| Metric | Value | Source |
| :--- | :---: | :--- |
| **Forecast Accuracy (100 - MAPE)** | **90.20%** | `backend/ml/metrics.json` |
| **Test Set MAPE** | **0.0980** | `backend/ml/metrics.json` |
| **Cash-Out Incidents Reduced** | Not measured | No verified outcome metric is available |

---

## 🛠️ Tech Stack

- **Frontend**: React (Vite), React Router, Axios, `react-plotly.js` + `plotly.js-dist-min` for charts, plain CSS design system (dark navy `#0F172A`, light background `#F8FAFC`, white rounded cards, teal accent `#0F766E`, red high-risk alerts).
- **Backend**: Python FastAPI, SQLAlchemy + PyMySQL, Pydantic, python-jose (JWT), direct bcrypt hashing.
- **Database**: MySQL (configured through backend environment variables); dataset tables are `ds_atms`, `ds_demand_records`, and `ds_forecasts`.
- **Data & ML**: Pandas, NumPy, scikit-learn (`GradientBoostingRegressor`), joblib; Google OR-Tools for TSP/VRP replenishment route optimization.
- **DevOps**: `Dockerfile` for backend and frontend, `docker-compose.yml`, automated E2E test suite.

---

## 📊 Dataset & Feature Engineering

The source file `ATM_cash_demand.csv` contains 35,598 rows. The processed file `backend/outputs/cleaned_data.csv` contains 35,072 records across 28 columns, 32 ATMs, and dates from 2023-01-01 through 2025-12-31. `withdrawal_amount` is the target; the cleaned data has no duplicate `(atm_id, date)` keys. `holiday_name` is the only field with missing values.

| Column | Real Type | Usage in Koshflow |
| :--- | :--- | :--- |
| `atm_id` | String (`ATM001` - `ATM032`) | Unique ATM network identifier and categorical encoding. |
| `date` | Date (`2023-01-01` to `2025-12-31`) | Parsed into `day_of_week`, `is_weekend`, `day_of_month`, `month`. |
| `city` | String (Mumbai, Delhi, Jaipur...) | Geographical clustering and location display. |
| `location_type` | String (`Metro`, `Urban`, `Semi-urban`, `Rural`) | Locational withdrawal elasticity factor. |
| `site_type` | String (`Branch`, `Market`, `Street`...) | Footfall profile categorization. |
| `latitude`, `longitude` | Float | Vehicle Routing Problem coordinates for Google OR-Tools. |
| `atm_capacity` | Integer (e.g. ₹2,500,000) | ATM cash capacity used to compute target refill limits. |
| `nearby_atm_count` | Integer | Competitor cash access density. |
| `withdrawal_amount` | Float | **Target variable**: actual daily cash demand. |
| `balance_closing` | Float | **Cash Left**: current remaining balance in ATM. |
| `is_salary_day` | Binary (0 / 1) | Demand surge indicator on 1st-5th & month-end. |
| `is_holiday` / `is_festival` | Binary / Float | Holiday demand dampening/surges. |
| `temperature`, `rainfall`, `footfall_index` | Float | Weather & footfall activity predictors. |
| `upi_share_pct` | Float | Digital transaction density vs cash reliance. |
| *Engineered Lags* | Float (`lag_1`, `lag_7`, `roll_mean_7`) | Momentum and seasonal cash withdrawal signals. |

### ⚠️ Risk Level Classification Rule
- **High Risk (Red)**: Predicted run-out within **$\le 1.0$ day** (`cash_left <= 1.0 * predicted_daily_demand`). Urgent replenishment needed.
- **Medium Risk (Amber)**: Predicted run-out within **$2.0 - 3.0$ days** (`cash_left <= 3.0 * predicted_daily_demand`). Scheduled refill.
- **Normal Risk (Green)**: Safe cash buffer (**$> 3.0$ days**).

---

## 🗂️ Project Structure

```
Kosh Flow/
├── ATM_cash_demand.csv          # Source dataset (35,598 rows)
├── docker-compose.yml           # Multi-container orchestration (MySQL, Backend, Frontend)
├── README.md                    # Setup and architectural documentation
├── backend/
│   ├── 2_load_to_mysql.py       # Non-destructive, idempotent dataset importer
│   ├── outputs/cleaned_data.csv # Processed dataset (35,072 rows, 28 columns)
│   ├── .env.example             # Database & JWT environment template
│   ├── Dockerfile               # Backend container specification
│   ├── requirements.txt         # Python dependencies
│   ├── test_e2e.py              # Automated 10-point end-to-end integration test
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, lifespan table creation, routers
│   │   ├── config.py            # Environment loader reading backend/.env
│   │   ├── database.py          # SQLAlchemy engine, session factory, auto table creation
│   │   ├── models.py            # User, ATM, DemandRecord, Forecast, Alert tables
│   │   ├── schemas.py           # Pydantic validation schemas
│   │   ├── auth.py              # Bcrypt hashing, JWT generation & get_current_user dependency
│   │   ├── services/
│   │   │   ├── forecast_service.py # Loads model.joblib, predicts demand, calculates refill
│   │   │   └── route_service.py    # Google OR-Tools TSP route solver (Depot -> ATMs -> Depot)
│   │   └── routers/
│   │       ├── auth_router.py      # /auth/register, /auth/login, /auth/me
│   │       ├── dashboard_router.py # /dashboard/kpis, /dashboard/demand, /dashboard/refill-atms
│   │       ├── forecast_router.py  # /forecast/atm/{atm_id}
│   │       ├── plan_router.py      # /plan, /plan/route
│   │       ├── model_router.py     # /model/metrics
│   │       ├── alerts_router.py    # /alerts
│   │       ├── dataset_router.py   # Public read-only, dataset-backed /api routes
│   │       └── demo_router.py      # /demo/... compatibility routes
│   ├── ml/
│   │   ├── train_model.py       # Cleaning, feature engineering, regression training
│   │   ├── model.joblib         # Serialized model & encoders bundle
│   │   └── metrics.json         # Evaluation metrics & targets
│   └── scripts/
│       └── seed_db.py           # Legacy ORM-table seeding utility
└── frontend/
    ├── Dockerfile               # Production multi-stage build with Nginx
    ├── package.json             # React, Vite, Axios, React Router, Plotly, Lucide
    ├── src/
    │   ├── api/client.js        # Axios instance with Bearer JWT interceptor
    │   ├── context/AuthContext.jsx # Authentication state provider
    │   ├── components/
    │   │   ├── Layout.jsx       # Dark navy sidebar + top notification navbar
    │   │   ├── Sidebar.jsx      # Navigation links in required order
    │   │   ├── TopNavbar.jsx    # Bell icon, red badge, latest alert, View all modal
    │   │   ├── AlertModal.jsx   # Active alerts dialog
    │   │   ├── PlotlyChart.jsx  # Plotly chart wrapper with resize handling
    │   │   └── ProtectedRoute.jsx # Route guard for authenticated pages
    │   ├── pages/
    │   │   ├── LoginPage.jsx    # Centered login card with demo fill helper
    │   │   ├── DashboardPage.jsx# Dataset-backed KPIs, filters, charts, and risk table
    │   │   ├── DemoNetworkPage.jsx # ATM and forecast explorer
    │   │   ├── DemoAnalyticsPage.jsx # Historical analytics and reports
    │   │   ├── PlanPage.jsx     # Suggested refills & OR-Tools route itinerary
    │   │   ├── ModelPage.jsx    # 3 metric cards & target validation note
    │   │   └── AboutPage.jsx    # Pipeline walkthrough & strategic goals
    │   ├── App.jsx              # Application router
    │   └── index.css            # Custom plain CSS design system
```

---

## ⚡ Quick Start & Run Commands

### 1. Database Configuration
Configure the backend environment with the MySQL connection settings and JWT secret provided by your deployment environment. Do not commit credentials:
```env
<<<<<<< HEAD

*(If MySQL is not currently connected, Koshflow automatically uses its built-in SQLite engine at `backend/koshflow.db` so we  can develop and test immediately without errors.)*
=======
DB_HOST=<mysql-host>
DB_PORT=<mysql-port>
DB_USER=<mysql-user>
DB_PASSWORD=<mysql-password>
DB_NAME=<mysql-database>
JWT_SECRET=<strong-secret>
JWT_EXPIRE_MINUTES=1440
```
>>>>>>> 5df26d1 (Update dashboard KPIs, forecast filters and ATM table)

### 2. Backend Setup
In my terminal:
```bash
# 1. Create and activate Python virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Import the cleaned data into the configured MySQL database
python backend/2_load_to_mysql.py

# 4. Start the FastAPI backend server
uvicorn app.main:app --app-dir backend --reload --port 8000
```
- The importer adds data to `ds_atms`, `ds_demand_records`, and `ds_forecasts` in batches, skipping existing natural keys; it does not drop tables or delete existing rows.
- The backend loads the existing `backend/ml/model.joblib` model. Do not retrain it as part of deployment.
- API Swagger Documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 3. Frontend Setup
In a second terminal:
```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Start the Vite React development server
npm run dev
```
Open your browser at **`http://localhost:5173`**.

---

## 🔑 Demo User Credentials

The database comes pre-seeded with an operator account:
- **Email**: `demo@koshflow.com`
- **Password**: `password123`
- *(Or click the "Fill Demo Login" button on the sign-in screen)*

## 🌐 Public Read-Only Demo

The login page's **Explore Demo Dashboard** button opens a public, read-only session without requiring an administrator JWT. The dashboard reads actual database-backed results through these GET endpoints:
- `GET /api/dashboard/summary`
- `GET /api/atms`
- `GET /api/analytics`
- `GET /api/forecast`
- `GET /api/atms/{atm_id}/history`
- Additional read-only alert, replenishment, and model-metric endpoints under `/api`.

The existing `/demo/...` endpoints remain as compatibility routes and now use the same dataset-backed service. Demo requests are restricted to GET operations; existing administrator authentication and JWT-protected routes remain available.

The active inference artifact is `backend/ml/model.joblib` (a `GradientBoostingRegressor` bundle with 19 expected features). Historical dashboard forecasts come from `ds_forecasts`; future forecasts are calculated from the loaded model and recent observed features. The API reports an error instead of returning invented predictions if the model is missing or incompatible. Cash-out reduction is not measured by the current model.

For Vercel, set `VITE_API_URL` to the deployed Render API base URL and redeploy the frontend. Configure the MySQL and JWT environment variables only in Render; keep the Aiven database persistent and do not put credentials in frontend settings. No Vercel or Render deployment is performed by the local commands above.

To run the dataset-backed endpoint and inference tests from the `backend` directory:
```bash
python -m unittest test_demo
```

---

## 🧪 Automated End-to-End Verification

To verify that the frontend, backend, database, and machine learning components connect and function without errors, run the automated integration test:
```bash
python backend/test_e2e.py
```
This tests:
1. `GET /` — API health status.
2. `POST /auth/login` — Authentication & JWT creation.
3. `GET /auth/me` — Bearer token authorization.
4. `GET /dashboard/kpis` — Average daily demand, at-risk count, planned refills, and forecast accuracy.
5. `GET /dashboard/demand?range=1|7|14|30` — Plotly actual vs forecast series across all 4 time views.
6. `GET /dashboard/refill-atms` — Cash-left and predicted run-out table.
7. `GET /plan` — Suggested refill amounts with risk level badges.
8. `POST /plan/route` — Google OR-Tools multi-stop TSP route (Depot $\rightarrow$ ATMs $\rightarrow$ Depot) with distances and duration.
9. `GET /model/metrics` — Model metrics (cash-out reduction is not measured).
10. `GET /alerts` — Top notification bar alerts.

---

## 🐳 Docker Deployment

To launch the complete full-stack app (MySQL 8.0, FastAPI backend, and React frontend) using Docker Compose:
```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- MySQL Server: `localhost:3306`
