"""
Reads REAL numbers from the dataset tables created by 2_load_to_mysql.py
(ds_demand_records and ds_forecasts) and from outputs/metrics.json.
Used by the dashboard so the cards and graph show your cleaned data, not sample values.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent       # .../backend
METRICS_FILE = BACKEND_DIR / "outputs" / "metrics.json"           # written by 1_eda_clean_train.py

# The dataset is DAILY, so hourly values are an ESTIMATE: the latest day's real total
# is split with a typical ATM day shape (the six shares add up to 1.0).
HOUR_LABELS = ["1 AM", "5 AM", "9 AM", "1 PM", "5 PM", "9 PM"]
HOUR_SHARE = [0.05, 0.07, 0.20, 0.27, 0.27, 0.14]


def _to_date(value):
    """MySQL returns a datetime/date, SQLite returns text - accept both."""
    if isinstance(value, str):
        return datetime.strptime(value[:10], "%Y-%m-%d")
    return datetime(value.year, value.month, value.day)


def forecast_accuracy_pct(default=0.0):
    """Forecast accuracy (%) from the trained model's metrics.json."""
    try:
        data = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
        return float(data["forecast_accuracy_pct"])
    except Exception:
        return default


def avg_daily_demand_lakhs(db, days=30):
    """Average withdrawal per ATM per day (in lakhs) over the latest `days` days of the dataset."""
    latest = _to_date(db.execute(text("SELECT MAX(date) FROM ds_demand_records")).scalar())
    start = latest - timedelta(days=days)
    avg = db.execute(text("SELECT AVG(withdrawal_amount) FROM ds_demand_records WHERE date >= :s"),
                     {"s": start}).scalar()
    return round(float(avg) / 100000.0, 2)


def demand_series(db, time_range):
    """Actual vs forecast (lakhs, average per ATM per day) for the range 1, 7, 14 or 30 days."""
    rows = db.execute(text(
        "SELECT date, AVG(actual_amount), AVG(forecast_amount) FROM ds_forecasts "
        "GROUP BY date ORDER BY date")).fetchall()
    n = {"1": 1, "7": 7, "14": 14, "30": 30}[time_range]
    rows = rows[-n:]
    dates = [_to_date(r[0]) for r in rows]
    actual = [float(r[1]) / 100000.0 for r in rows]
    forecast = [float(r[2]) / 100000.0 for r in rows]

    if time_range == "1":                       # hourly view (estimated split of the latest real day)
        return (HOUR_LABELS,
                [round(actual[-1] * s, 2) for s in HOUR_SHARE],
                [round(forecast[-1] * s, 2) for s in HOUR_SHARE])
    if time_range == "7":
        labels = [d.strftime("%a") for d in dates]                   # Mon, Tue ...
    elif time_range == "14":
        labels = [f"Day {i}" for i in range(1, len(dates) + 1)]      # Day 1, Day 2 ...
    else:
        labels = [f"{d.day} {d.strftime('%b')}" for d in dates]      # 3 Dec, 4 Dec ...
    return labels, [round(v, 2) for v in actual], [round(v, 2) for v in forecast]


def atm_risk_table(db):
    """
    Risk for every ATM from REAL numbers:
      cash left       = latest closing balance of the ATM in the dataset
      expected demand = model forecast averaged over the latest 7 days of the dataset
      days left       = cash left / expected demand
    High: <= 1 day, Medium: <= 3 days, Normal: more than 3 days.
    """
    latest = _to_date(db.execute(text("SELECT MAX(date) FROM ds_forecasts")).scalar())
    cash = db.execute(text(
        "SELECT d.atm_id, d.balance_closing FROM ds_demand_records d "
        "JOIN (SELECT atm_id, MAX(date) AS md FROM ds_demand_records GROUP BY atm_id) m "
        "ON d.atm_id = m.atm_id AND d.date = m.md")).fetchall()
    demand = dict(db.execute(text(
        "SELECT atm_id, AVG(forecast_amount) FROM ds_forecasts WHERE date >= :s GROUP BY atm_id"),
        {"s": latest - timedelta(days=6)}).fetchall())
    info = {r[0]: (r[1], r[2], r[3], r[4], r[5]) for r in db.execute(text("SELECT atm_id, city, site_type, atm_capacity, latitude, longitude FROM ds_atms")).fetchall()}

    rows = []
    for atm_id, cash_left in cash:
        exp = float(demand.get(atm_id) or 300000.0)
        days = round(float(cash_left) / exp, 1)
        risk = "high" if days <= 1.0 else ("medium" if days <= 3.0 else "normal")
        city, site, cap, lat, lon = info.get(atm_id, ("", "", 0, 0, 0))
        rows.append({"atm_id": atm_id, "city": city, "site_type": site or "Branch",
                     "cash_left": round(float(cash_left), 2), "expected_demand": round(exp, 2),
                     "days_left": days, "risk_level": risk,
                     "atm_capacity": float(cap), "latitude": float(lat), "longitude": float(lon)})
    return rows
