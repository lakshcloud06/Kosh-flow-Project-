import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, ATM, DemandRecord, Alert
from app.schemas import KPIResponse, DemandChartResponse, RefillATM
from app.auth import get_current_user
from app.services.forecast_service import predict_atm_demand, evaluate_risk_level
from app.services import real_data

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/kpis", response_model=KPIResponse)
def get_dashboard_kpis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Network KPIs. Demand and accuracy are REAL (from the dataset tables and metrics.json)."""
    forecast_acc = real_data.forecast_accuracy_pct()
    avg_daily_demand_lakhs = real_data.avg_daily_demand_lakhs(db, days=30)   # last 30 days of data

    # ATMs at risk = high risk; refills planned = high + medium (cash lasts 3 days or less)
    table = real_data.atm_risk_table(db)
    atms_at_risk_count = sum(1 for r in table if r["risk_level"] == "high")
    refills_planned_count = sum(1 for r in table if r["risk_level"] in ("high", "medium"))

    return {
        "avg_daily_demand_lakhs": avg_daily_demand_lakhs,
        "atms_at_risk": atms_at_risk_count,
        "refills_planned_week": refills_planned_count,
        "forecast_accuracy": forecast_acc
    }

@router.get("/demand", response_model=DemandChartResponse)
def get_demand_series(
    time_range: str = Query("7", alias="range", pattern="^(1|7|14|30)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actual vs forecast demand in lakhs (average per ATM per day) from the real forecast table."""
    x_labels, actual_series, forecast_series = real_data.demand_series(db, time_range)
    return {
        "range": time_range,
        "x": x_labels,
        "actual": actual_series,
        "forecast": forecast_series
    }

@router.get("/refill-atms", response_model=List[RefillATM])
def get_refill_atms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ATMs that need cash soon (high or medium risk), most urgent first. Uses real cash and forecast."""
    results = []
    for r in real_data.atm_risk_table(db):
        if r["risk_level"] not in ("high", "medium"):
            continue
        days_left = r["days_left"]
        if days_left <= 0.2:
            runout_str = "Critical (< 6 hours)"
        elif days_left <= 1.0:
            runout_str = "Tomorrow (within 24h)"
        elif days_left <= 2.0:
            runout_str = "In 2 days"
        else:
            runout_str = f"In {int(round(days_left))} days"
        results.append({
            "atm_id": r["atm_id"],
            "location": f"{r['city']} ({r['site_type']})",
            "cash_left": r["cash_left"],
            "predicted_out": runout_str,
            "risk_level": r["risk_level"]
        })

    risk_order = {"high": 0, "medium": 1, "normal": 2}
    results.sort(key=lambda x: (risk_order.get(x["risk_level"], 2), x["cash_left"]))
    return results
