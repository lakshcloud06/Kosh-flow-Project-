from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.dataset_router import (
    get_dataset_alerts,
    get_dataset_analytics,
    get_dataset_atms,
    get_dataset_dashboard_summary,
    get_dataset_forecast,
    get_dataset_model_metrics,
    get_dataset_replenishment_plan,
    get_dataset_replenishment_route,
)

router = APIRouter(prefix="/demo", tags=["Public Demo"])


@router.get("/dashboard/kpis")
def get_demo_kpis(db: Session = Depends(get_db)):
    summary = get_dataset_dashboard_summary(db)
    return {
        "avg_daily_demand_lakhs": (
            round(summary["average_daily_withdrawal"] / 100000, 2)
            if summary["average_daily_withdrawal"] is not None else None
        ),
        "atms_at_risk": summary["atms_at_risk"],
        "refills_planned_week": summary["refill_recommendations"],
        "forecast_accuracy": summary["forecast_accuracy"],
    }


@router.get("/dashboard/demand")
def get_demo_demand(
    time_range: str = Query("7", alias="range", pattern="^(1|7|14|30)$"),
    db: Session = Depends(get_db),
):
    latest = db.execute(text("SELECT MAX(date) FROM ds_demand_records")).scalar()
    if latest is None:
        return {"range": time_range, "x": [], "actual": [], "forecast": []}
    end_date = latest.date() if hasattr(latest, "date") else date.fromisoformat(str(latest)[:10])
    days = {"1": 1, "7": 7, "14": 14, "30": 30}[time_range]
    series = get_dataset_analytics(
        start_date=end_date - timedelta(days=days - 1),
        end_date=end_date,
        group_by="date",
        db=db,
    )["data"]
    return {
        "range": time_range,
        "x": [item["date"] for item in series],
        "actual": [item["actual_withdrawal"] / 100000 for item in series],
        "forecast": [
            item["predicted_demand"] / 100000 if item["predicted_demand"] is not None else None
            for item in series
        ],
    }


@router.get("/dashboard/refill-atms")
def get_demo_refill_atms(db: Session = Depends(get_db)):
    return [
        {
            "atm_id": atm["atm_id"],
            "location": f'{atm["city"]} ({atm["site_type"] or "Branch"})',
            "cash_left": atm["cash_left"],
            "predicted_out": (
                f'In {atm["days_left"]:.1f} days'
                if atm["days_left"] is not None else "Unavailable"
            ),
            "risk_level": atm["risk_level"],
        }
        for atm in get_dataset_atms(db=db)
        if atm["risk_level"] in ("high", "medium")
    ]


@router.get("/plan")
def get_demo_plan(db: Session = Depends(get_db)):
    return get_dataset_replenishment_plan(db)


@router.get("/plan/route")
def get_demo_route(db: Session = Depends(get_db)):
    return get_dataset_replenishment_route(db)


@router.get("/model/metrics")
def get_demo_model_metrics():
    return get_dataset_model_metrics()


@router.get("/alerts")
def get_demo_alerts(db: Session = Depends(get_db)):
    return get_dataset_alerts(db)


@router.get("/atms")
def get_demo_atms(
    city: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return get_dataset_atms(city=city, region=region, db=db)


@router.get("/forecast/atm/{atm_id}")
def get_demo_atm_forecast(
    atm_id: str,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    result = get_dataset_forecast(atm_id=atm_id, days=days, db=db)
    return {
        "atm_id": atm_id,
        "city": next(
            (atm["city"] for atm in get_dataset_atms(db=db) if atm["atm_id"] == atm_id),
            None,
        ),
        "forecast_origin_date": result["forecast_origin_date"],
        "forecasts": result["items"],
    }


@router.get("/forecast/region")
def get_demo_region_forecast(
    region: str = Query("All"),
    db: Session = Depends(get_db),
):
    atms = get_dataset_atms(db=db)
    selected = atms if region == "All" else [
        atm for atm in atms if atm["region"].casefold() == region.casefold()
    ]
    if not selected:
        raise HTTPException(status_code=404, detail="No ATM records exist for this region.")
    demand = [atm["average_daily_demand"] for atm in selected if atm["average_daily_demand"] is not None]
    return {
        "region": region,
        "atm_count": len(selected),
        "average_daily_demand": sum(demand) / len(demand) if demand else None,
        "at_risk": sum(atm["risk_level"] == "high" for atm in selected),
        "locations": [
            {
                "atm_id": atm["atm_id"],
                "city": atm["city"],
                "predicted_demand": atm["average_daily_demand"],
                "cash_left": atm["cash_left"],
                "risk_level": atm["risk_level"],
            }
            for atm in selected
        ],
    }


@router.get("/analytics")
def get_demo_analytics(
    days: str = Query("30", alias="range", pattern="^(7|30|90)$"),
    db: Session = Depends(get_db),
):
    latest = db.execute(text("SELECT MAX(date) FROM ds_demand_records")).scalar()
    if latest is None:
        return {"range": int(days), "x": [], "actual": [], "forecast": []}
    end_date = latest.date() if hasattr(latest, "date") else date.fromisoformat(str(latest)[:10])
    series = get_dataset_analytics(
        start_date=end_date - timedelta(days=int(days) - 1),
        end_date=end_date,
        group_by="date",
        db=db,
    )["data"]
    return {
        "range": int(days),
        "x": [item["date"] for item in series],
        "actual": [item["actual_withdrawal"] / 100000 for item in series],
        "forecast": [
            item["predicted_demand"] / 100000 if item["predicted_demand"] is not None else None
            for item in series
        ],
    }
