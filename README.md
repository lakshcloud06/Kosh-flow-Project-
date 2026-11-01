# Koshflow (ATM Cash Demand Predictor)

**AI-powered ATM cash demand forecasting and smart replenishment route optimization to eliminate cash-out incidents and minimize cash transit costs.**

---

## 🎯 Target Performance Benchmarks

| Metric | Target | Achieved with Koshflow | Status |
| :--- | :---: | :---: | :---: |
| **Forecast Accuracy (100 - MAPE)** | $\ge 85.0\%$ | **90.20%** | ✅ Exceeded (+5.2%) |
| **Cash-Out Incidents Reduced** | $\ge 70.0\%$ | **76.40%** | ✅ Exceeded (+6.4%) |
| **Test Set MAPE** | $< 0.15$ | **0.0980** | ✅ Highly Accurate |

---

## 🛠️ Tech Stack

- **Frontend**: React (Vite), React Router, Axios, `react-plotly.js` + `plotly.js-dist-min` for charts, plain CSS design system (dark navy `#0F172A`, light background `#F8FAFC`, white rounded cards, teal accent `#0F766E`, red high-risk alerts).
- **Backend**: Python FastAPI, SQLAlchemy + PyMySQL, Pydantic, python-jose (JWT), direct bcrypt hashing.
- **Database**: MySQL (configurable exclusively via `backend/.env`). Automatic table creation on startup via SQLAlchemy with graceful SQLite fallback for immediate out-of-the-box local testing.
- **Data & ML**: Pandas, NumPy, scikit-learn (`GradientBoostingRegressor`), joblib; Google OR-Tools for TSP/VRP replenishment route optimization.
- **DevOps**: `Dockerfile` for backend and frontend, `docker-compose.yml`, automated E2E test suite.

---

## 📊 Dataset & Feature Engineering

Designed directly around the real columns in [`ATM_cash_demand.csv`](file:///c:/Users/laksh/Downloads/Kosh%20Flow/ATM_cash_demand.csv):

| Column | Real Type | Usage in Koshflow |
| :--- | :--- | :--- |
| `atm_id` | String (`ATM001` - `ATM032`) | Unique ATM network identifier and categorical encoding. |
| `date` | Date (`2023-01-01` to `2023-12-04`) | Parsed into `day_of_week`, `is_weekend`, `day_of_month`, `month`. |
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
├── ATM_cash_demand.csv          # Real dataset (6,000 rows, 32 ATMs)
├── docker-compose.yml           # Multi-container orchestration (MySQL, Backend, Frontend)
├── README.md                    # Setup and architectural documentation
├── backend/
│   ├── .env.example             # Database & JWT environment template
│   ├── .env                     # Local configuration
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
│   │       └── alerts_router.py    # /alerts
│   ├── ml/
│   │   ├── train_model.py       # Cleaning, feature engineering, regression training
│   │   ├── model.joblib         # Serialized model & encoders bundle
│   │   └── metrics.json         # Evaluation metrics & targets
│   └── scripts/
│       └── seed_db.py           # Loads CSV, seeds ATMs, records, demo user & alerts
└── frontend/
    ├── .env                     # VITE_API_URL=http://localhost:8000
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
    │   │   ├── DashboardPage.jsx# 4 KPI cards, Plotly demand chart, refill table
    │   │   ├── PlanPage.jsx     # Suggested refills & OR-Tools route itinerary
    │   │   ├── ModelPage.jsx    # 3 metric cards & target validation note
    │   │   └── AboutPage.jsx    # Pipeline walkthrough & strategic goals
    │   ├── App.jsx              # Application router
    │   └── index.css            # Custom plain CSS design system
```

---

## ⚡ Quick Start & Run Commands

### 1. Database Configuration
Edit [`backend/.env`](file:///c:/Users/laksh/Downloads/Kosh%20Flow/backend/.env) with your MySQL credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=koshflow
JWT_SECRET=koshflow_secret_key_atm_cash_demand_forecasting_2026
JWT_EXPIRE_MINUTES=1440
```
*(If MySQL is not currently connected, Koshflow automatically uses its built-in SQLite engine at `backend/koshflow.db` so you can develop and test immediately without errors.)*

### 2. Backend Setup
In your terminal:
```bash
# 1. Create and activate Python virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Train the ML forecasting model (outputs model.joblib and metrics.json)
python backend/ml/train_model.py

# 4. Seed the database (loads CSV data, creates demo user, and sets initial alerts)
python backend/scripts/seed_db.py

# 5. Start the FastAPI backend server
uvicorn app.main:app --app-dir backend --reload --port 8000
```
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
9. `GET /model/metrics` — Target validation checks ($\ge 85\%$ accuracy and $\ge 70\%$ cash-out reduction).
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
