import json
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.forecast_service import (
    ModelUnavailableError,
    compute_suggested_refill,
    evaluate_risk_level,
    get_model_bundle,
    predict_atm_demand,
)
from app.services.route_service import optimize_refill_route

logger = logging.getLogger("koshflow.dataset_api")
router = APIRouter(prefix="/api", tags=["Dataset"])
BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_METRICS_FILE = BACKEND_DIR / "ml" / "metrics.json"

CITY_REGIONS = {
    "Barabanki": "North",
    "Bareilly": "North",
    "Bengaluru": "South",
    "Delhi": "North",
    "Ghaziabad": "North",
    "Gorakhpur": "North",
    "Indore": "Central",
    "Jaipur": "North",
    "Kolkata": "East",
    "Lucknow": "North",
    "Mathura": "North",
    "Mumbai": "West",
    "Nagpur": "West",
    "Patna": "East",
    "Rewa": "Central",
    "Sitapur": "North",
}


def _iso_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _region_for_city(city):
    return CITY_REGIONS.get(city, "Unmapped")


def _model_metrics(required=False):
    if not MODEL_METRICS_FILE.exists():
        if required:
            raise HTTPException(status_code=503, detail="Model evaluation metrics are unavailable.")
        return None
    try:
        return json.loads(MODEL_METRICS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Unable to read model evaluation metrics.")
        if required:
            raise HTTPException(status_code=503, detail="Model evaluation metrics are unavailable.") from exc
        return None


def _latest_snapshot(db):
    latest_forecast = db.execute(text("SELECT MAX(date) FROM ds_forecasts")).scalar()
    latest_forecast_date = (
        date.fromisoformat(_iso_date(latest_forecast)) if latest_forecast else None
    )
    forecast_start = (
        latest_forecast_date - timedelta(days=6) if latest_forecast_date else None
    )
    forecast_by_atm = {}
    if forecast_start:
        forecast_by_atm = dict(db.execute(
            text(
                "SELECT atm_id, AVG(forecast_amount) "
                "FROM ds_forecasts WHERE date >= :start_date GROUP BY atm_id"
            ),
            {"start_date": forecast_start},
        ).all())

    latest_cash = db.execute(text(
        "SELECT d.atm_id, d.date, d.balance_closing "
        "FROM ds_demand_records d "
        "JOIN (SELECT atm_id, MAX(date) AS latest_date "
        "      FROM ds_demand_records GROUP BY atm_id) latest "
        "ON latest.atm_id = d.atm_id AND latest.latest_date = d.date"
    )).all()
    cash_by_atm = {row[0]: (row[1], row[2]) for row in latest_cash}

    atms = db.execute(text(
        "SELECT atm_id, city, location_type, site_type, latitude, longitude, "
        "atm_capacity, nearby_atm_count FROM ds_atms ORDER BY atm_id"
    )).all()
    results = []
    for row in atms:
        atm_id, city = row[0], row[1]
        latest_record = cash_by_atm.get(atm_id)
        cash_left = float(latest_record[1]) if latest_record and latest_record[1] is not None else None
        expected_demand = forecast_by_atm.get(atm_id)
        if expected_demand is not None:
            expected_demand = float(expected_demand)

        if cash_left is None or expected_demand is None or expected_demand <= 0:
            risk_level, days_left = "unavailable", None
        else:
            risk_level, days_left = evaluate_risk_level(cash_left, expected_demand)

        results.append({
            "atm_id": atm_id,
            "city": city,
            "region": _region_for_city(city),
            "location_type": row[2],
            "site_type": row[3],
            "latitude": float(row[4]) if row[4] is not None else None,
            "longitude": float(row[5]) if row[5] is not None else None,
            "atm_capacity": float(row[6]) if row[6] is not None else None,
            "nearby_atm_count": int(row[7]) if row[7] is not None else None,
            "cash_left": cash_left,
            "cash_as_of": _iso_date(latest_record[0]) if latest_record else None,
            "average_daily_demand": expected_demand,
            "days_left": days_left,
            "risk_level": risk_level,
        })
    return results, _iso_date(latest_forecast)


def _dataset_date_range(db):
    row = db.execute(text(
        "SELECT MIN(date), MAX(date) FROM ds_demand_records"
    )).one()
    return _iso_date(row[0]), _iso_date(row[1])


@router.get("/dashboard/summary")
def get_dataset_dashboard_summary(db: Session = Depends(get_db)):
    row = db.execute(text(
        "SELECT COUNT(*), COUNT(DISTINCT atm_id), AVG(withdrawal_amount), "
        "SUM(cash_replenished), MIN(date), MAX(date) FROM ds_demand_records"
    )).one()
    atms, _ = _latest_snapshot(db)
    metrics = _model_metrics()
    return {
        "total_atms": int(db.execute(text("SELECT COUNT(*) FROM ds_atms")).scalar() or 0),
        "total_records": int(row[0] or 0),
        "atms_with_records": int(row[1] or 0),
        "average_daily_withdrawal": round(float(row[2]), 2) if row[2] is not None else None,
        "total_cash_replenishment": round(float(row[3]), 2) if row[3] is not None else None,
        "atms_at_risk": sum(atm["risk_level"] == "high" for atm in atms),
        "refill_recommendations": sum(atm["risk_level"] in ("high", "medium") for atm in atms),
        "date_start": _iso_date(row[4]),
        "date_end": _iso_date(row[5]),
        "model_name": metrics.get("model_name") if metrics else None,
        "model_accuracy": metrics.get("model_accuracy") if metrics else None,
        "forecast_accuracy": metrics.get("forecast_accuracy") if metrics else None,
        "model_metrics_available": metrics is not None,
    }


@router.get("/atms")
def get_dataset_atms(
    city: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
):
    atms, _ = _latest_snapshot(db)
    if city:
        atms = [atm for atm in atms if atm["city"] == city]
    if region:
        atms = [atm for atm in atms if atm["region"].casefold() == region.casefold()]
    return atms


@router.get("/analytics")
def get_dataset_analytics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    atm_id: Optional[str] = None,
    city: Optional[str] = None,
    group_by: str = Query("date", pattern="^(date|city|region|atm)$"),
    db: Session = Depends(get_db),
):
    data_start, data_end = _dataset_date_range(db)
    if data_start is None:
        return {"start_date": None, "end_date": None, "group_by": group_by, "data": []}

    start = start_date or date.fromisoformat(data_start)
    end = end_date or date.fromisoformat(data_end)
    if start > end:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date.")

    rows = db.execute(text(
        "SELECT d.atm_id, a.city, DATE(d.date), d.withdrawal_amount, f.forecast_amount "
        "FROM ds_demand_records d "
        "JOIN ds_atms a ON a.atm_id = d.atm_id "
        "LEFT JOIN ds_forecasts f ON f.atm_id = d.atm_id AND f.date = d.date "
        "WHERE d.date >= :start_date AND d.date <= :end_date "
        "AND (:atm_id IS NULL OR d.atm_id = :atm_id) "
        "AND (:city IS NULL OR a.city = :city) "
        "ORDER BY d.date, d.atm_id"
    ), {
        "start_date": start,
        "end_date": end,
        "atm_id": atm_id,
        "city": city,
    }).all()

    grouped = {}
    for row in rows:
        row_atm, row_city, row_date = row[0], row[1], _iso_date(row[2])
        if group_by == "date":
            key = row_date
        elif group_by == "city":
            key = row_city
        elif group_by == "region":
            key = _region_for_city(row_city)
        else:
            key = row_atm

        item = grouped.setdefault(key, {
            "actual_withdrawal": 0.0,
            "predicted_demand": 0.0,
            "forecast_records": 0,
            "atm_ids": set(),
            "cities": set(),
            "dates": set(),
        })
        item["actual_withdrawal"] += float(row[3] or 0)
        item["atm_ids"].add(row_atm)
        item["cities"].add(row_city)
        item["dates"].add(row_date)
        if row[4] is not None:
            item["predicted_demand"] += float(row[4])
            item["forecast_records"] += 1

    data = []
    for key, values in grouped.items():
        item = {
            "actual_withdrawal": round(values["actual_withdrawal"], 2),
            "predicted_demand": round(values["predicted_demand"], 2) if values["forecast_records"] else None,
            "forecast_records": values["forecast_records"],
            "atm_count": len(values["atm_ids"]),
        }
        if group_by == "date":
            item["date"] = key
        elif group_by == "city":
            item["city"] = key
            item["region"] = _region_for_city(key)
        elif group_by == "region":
            item["region"] = key
            item["cities"] = sorted(values["cities"])
        else:
            item["atm_id"] = key
            item["city"] = next(iter(values["cities"]))
            item["region"] = _region_for_city(item["city"])
        data.append(item)

    if group_by == "date":
        data.sort(key=lambda item: item["date"])
    else:
        data.sort(key=lambda item: item.get(group_by, item.get("atm_id", "")))

    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "group_by": group_by,
        "filters": {"atm_id": atm_id, "city": city},
        "data": data,
    }


@router.get("/atms/{atm_id}/history")
def get_atm_history(
    atm_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    atm = db.execute(text(
        "SELECT atm_id, city FROM ds_atms WHERE atm_id = :atm_id"
    ), {"atm_id": atm_id}).first()
    if not atm:
        raise HTTPException(status_code=404, detail=f"ATM '{atm_id}' was not found.")

    data_start, data_end = _dataset_date_range(db)
    if data_start is None:
        return {"atm_id": atm_id, "city": atm[1], "data": []}
    start = start_date or date.fromisoformat(data_start)
    end = end_date or date.fromisoformat(data_end)
    if start > end:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date.")

    rows = db.execute(text(
        "SELECT DATE(d.date), d.withdrawal_amount, d.cash_replenished, "
        "d.balance_closing, f.forecast_amount "
        "FROM ds_demand_records d "
        "LEFT JOIN ds_forecasts f ON f.atm_id = d.atm_id AND f.date = d.date "
        "WHERE d.atm_id = :atm_id AND d.date >= :start_date AND d.date <= :end_date "
        "ORDER BY d.date"
    ), {"atm_id": atm_id, "start_date": start, "end_date": end}).all()
    return {
        "atm_id": atm_id,
        "city": atm[1],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "data": [{
            "date": _iso_date(row[0]),
            "withdrawal_amount": float(row[1]) if row[1] is not None else None,
            "cash_replenished": float(row[2]) if row[2] is not None else None,
            "balance_closing": float(row[3]) if row[3] is not None else None,
            "predicted_demand": float(row[4]) if row[4] is not None else None,
        } for row in rows],
    }


def _forecast_for_atm(db, atm, days, start_date):
    rows = db.execute(text(
        "SELECT date, withdrawal_amount, temperature, rainfall, footfall_index, "
        "upi_share_pct FROM ds_demand_records "
        "WHERE atm_id = :atm_id ORDER BY date DESC LIMIT 30"
    ), {"atm_id": atm["atm_id"]}).all()
    observations = list(reversed(rows))
    if len(observations) < 7:
        raise HTTPException(
            status_code=422,
            detail=f"ATM '{atm['atm_id']}' has fewer than seven historical records for inference.",
        )

    latest_values = observations[-1]
    feature_names = ("temperature", "rainfall", "footfall_index", "upi_share_pct")
    feature_values = {}
    for index, name in enumerate(feature_names, start=2):
        value = latest_values[index]
        if value is None:
            raise HTTPException(
                status_code=422,
                detail=f"ATM '{atm['atm_id']}' is missing required historical feature '{name}'.",
            )
        feature_values[name] = float(value)

    history = [float(row[1]) for row in observations]
    current_cash = atm["cash_left"]
    if current_cash is None:
        raise HTTPException(status_code=422, detail=f"ATM '{atm['atm_id']}' has no closing balance.")
    if not atm["location_type"] or atm["atm_capacity"] is None or atm["nearby_atm_count"] is None:
        raise HTTPException(status_code=422, detail=f"ATM '{atm['atm_id']}' is missing model metadata.")

    forecasts = []
    for offset in range(days):
        target_date = start_date + timedelta(days=offset)
        recent_lags = {
            "lag_1": history[-1],
            "lag_7": history[-7],
            "roll_mean_7": sum(history[-7:]) / 7,
            **feature_values,
            "is_holiday": 0,
            "is_festival": 0,
        }
        try:
            prediction = predict_atm_demand(
                atm["atm_id"],
                atm["city"],
                atm["location_type"],
                atm["atm_capacity"],
                atm["nearby_atm_count"],
                target_date,
                recent_lags,
            )
        except ModelUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        current_cash = max(0.0, current_cash - prediction)
        risk_level, days_left = evaluate_risk_level(current_cash, prediction)
        forecasts.append({
            "atm_id": atm["atm_id"],
            "date": target_date.isoformat(),
            "day_name": target_date.strftime("%a"),
            "predicted_demand": prediction,
            "projected_cash_left": round(current_cash, 2),
            "days_left": days_left,
            "risk_level": risk_level,
        })
        history.append(prediction)
    return forecasts


@router.get("/forecast")
def get_dataset_forecast(
    atm_id: Optional[str] = None,
    days: int = Query(7, ge=1, le=30),
    start_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    try:
        get_model_bundle()
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    atms, _ = _latest_snapshot(db)
    if atm_id:
        atms = [atm for atm in atms if atm["atm_id"] == atm_id]
        if not atms:
            raise HTTPException(status_code=404, detail=f"ATM '{atm_id}' was not found.")
    if not atms:
        return {"forecast_origin_date": None, "days": days, "items": []}

    latest_date = max(date.fromisoformat(atm["cash_as_of"]) for atm in atms if atm["cash_as_of"])
    origin_date = latest_date
    first_forecast_date = start_date or (origin_date + timedelta(days=1))
    if first_forecast_date <= origin_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must be after the latest available dataset date.",
        )
    items = []
    for atm in atms:
        items.extend(_forecast_for_atm(db, atm, days, first_forecast_date))
    return {
        "forecast_origin_date": origin_date.isoformat(),
        "days": days,
        "assumptions": (
            "Future weather and footfall use each ATM's latest observed values; "
            "future holiday and festival flags are neutral because those dates are not in the dataset."
        ),
        "items": items,
    }


@router.get("/alerts")
def get_dataset_alerts(db: Session = Depends(get_db)):
    atms, _ = _latest_snapshot(db)
    alerts = []
    for atm in atms:
        if atm["risk_level"] not in ("high", "medium"):
            continue
        days_left = atm["days_left"]
        if days_left <= 0.25:
            message = f"{atm['atm_id']} ({atm['city']}) is projected to run out in less than 6 hours."
        elif days_left <= 1:
            message = f"{atm['atm_id']} ({atm['city']}) is projected to run out within 24 hours."
        else:
            message = f"{atm['atm_id']} ({atm['city']}) has {days_left:.1f} days of projected cash remaining."
        alerts.append({
            "id": len(alerts) + 1,
            "atm_id": atm["atm_id"],
            "message": message,
            "risk_level": atm["risk_level"],
            "cash_left": atm["cash_left"],
            "predicted_runout_days": days_left,
            "created_at": atm["cash_as_of"],
        })
    return alerts


@router.get("/plan")
def get_dataset_replenishment_plan(db: Session = Depends(get_db)):
    atms, _ = _latest_snapshot(db)
    plan = []
    for atm in atms:
        if atm["risk_level"] == "unavailable":
            continue
        add_cash = compute_suggested_refill(
            atm["atm_capacity"], atm["cash_left"], atm["risk_level"]
        )
        plan.append({
            "atm_id": atm["atm_id"],
            "location": f"{atm['city']} ({atm['site_type'] or 'Branch'})",
            "cash_left": atm["cash_left"],
            "add_cash": add_cash,
            "risk_level": atm["risk_level"],
            "predicted_demand": atm["average_daily_demand"],
        })
    priority = {"high": 0, "medium": 1, "normal": 2}
    plan.sort(key=lambda item: (priority[item["risk_level"]], -item["add_cash"]))
    return plan


@router.get("/plan/route")
def get_dataset_replenishment_route(db: Session = Depends(get_db)):
    atms, _ = _latest_snapshot(db)
    stops = [{
        "atm_id": atm["atm_id"],
        "city": atm["city"],
        "site_type": atm["site_type"],
        "location": f"{atm['city']} ({atm['site_type'] or 'Branch'})",
        "latitude": atm["latitude"],
        "longitude": atm["longitude"],
        "current_cash": atm["cash_left"],
        "atm_capacity": atm["atm_capacity"],
    } for atm in atms if atm["risk_level"] in ("high", "medium")]
    if any(stop["latitude"] is None or stop["longitude"] is None for stop in stops):
        raise HTTPException(status_code=503, detail="ATM coordinates are unavailable for route planning.")
    return optimize_refill_route(stops)


@router.get("/model/metrics")
def get_dataset_model_metrics():
    metrics = _model_metrics(required=True)
    try:
        bundle = get_model_bundle()
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "model_name": metrics["model_name"],
        "model_accuracy": metrics.get("model_accuracy"),
        "forecast_accuracy": metrics.get("forecast_accuracy"),
        "test_mape": metrics.get("test_mape"),
        "trained_at": metrics.get("trained_at"),
        "feature_columns": bundle["feature_columns"],
        "cash_out_reduced": None,
    }
