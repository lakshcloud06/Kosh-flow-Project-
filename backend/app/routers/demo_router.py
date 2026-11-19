from datetime import date, timedelta
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/demo", tags=["Public Demo"])

# Fictional, in-memory examples only. This router intentionally has no database,
# authentication, or write dependencies.
DEMO_ATMS = [
    {"atm_id": "DEMO-001", "city": "Mumbai", "region": "West", "site_type": "Metro", "latitude": 19.0760, "longitude": 72.8777, "atm_capacity": 2500000, "cash_left": 310000, "expected_demand": 420000, "risk_level": "high"},
    {"atm_id": "DEMO-002", "city": "Pune", "region": "West", "site_type": "Market", "latitude": 18.5204, "longitude": 73.8567, "atm_capacity": 2200000, "cash_left": 780000, "expected_demand": 300000, "risk_level": "medium"},
    {"atm_id": "DEMO-003", "city": "Jaipur", "region": "North", "site_type": "Branch", "latitude": 26.9124, "longitude": 75.7873, "atm_capacity": 2000000, "cash_left": 1650000, "expected_demand": 270000, "risk_level": "normal"},
    {"atm_id": "DEMO-004", "city": "Delhi", "region": "North", "site_type": "Metro", "latitude": 28.6139, "longitude": 77.2090, "atm_capacity": 2800000, "cash_left": 190000, "expected_demand": 390000, "risk_level": "high"},
    {"atm_id": "DEMO-005", "city": "Bengaluru", "region": "South", "site_type": "Business District", "latitude": 12.9716, "longitude": 77.5946, "atm_capacity": 2400000, "cash_left": 680000, "expected_demand": 285000, "risk_level": "medium"},
    {"atm_id": "DEMO-006", "city": "Chennai", "region": "South", "site_type": "Transit Hub", "latitude": 13.0827, "longitude": 80.2707, "atm_capacity": 2300000, "cash_left": 1450000, "expected_demand": 260000, "risk_level": "normal"},
]


def _series(days: int) -> Dict[str, List]:
    labels = []
    actual = []
    forecast = []
    today = date.today()
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        index = days - offset
        labels.append(day.strftime("%d %b"))
        actual.append(round(4.2 + (index % 7) * 0.19, 2))
        forecast.append(round(4.15 + (index % 7) * 0.18, 2))
    return {"x": labels, "actual": actual, "forecast": forecast}


def _refill_atms() -> List[dict]:
    return [
        {
            "atm_id": atm["atm_id"],
            "location": f'{atm["city"]} ({atm["site_type"]})',
            "cash_left": atm["cash_left"],
            "predicted_out": "Tomorrow (within 24h)" if atm["risk_level"] == "high" else "In 3 days",
            "risk_level": atm["risk_level"],
        }
        for atm in DEMO_ATMS
        if atm["risk_level"] in ("high", "medium")
    ]


@router.get("/dashboard/kpis")
def get_demo_kpis():
    return {
        "avg_daily_demand_lakhs": 4.86,
        "atms_at_risk": sum(atm["risk_level"] == "high" for atm in DEMO_ATMS),
        "refills_planned_week": sum(atm["risk_level"] in ("high", "medium") for atm in DEMO_ATMS),
        "forecast_accuracy": 90.2,
    }


@router.get("/dashboard/demand")
def get_demo_demand(time_range: str = Query("7", alias="range", pattern="^(1|7|14|30)$")):
    days = {"1": 1, "7": 7, "14": 14, "30": 30}[time_range]
    series = _series(days)
    if time_range == "1":
        return {"range": time_range, "x": ["1 AM", "5 AM", "9 AM", "1 PM", "5 PM", "9 PM"],
                "actual": [0.24, 0.34, 0.97, 1.31, 1.31, 0.68],
                "forecast": [0.23, 0.33, 0.95, 1.29, 1.30, 0.67]}
    return {"range": time_range, **series}


@router.get("/dashboard/refill-atms")
def get_demo_refill_atms():
    return _refill_atms()


@router.get("/plan")
def get_demo_plan():
    return [
        {
            "atm_id": atm["atm_id"],
            "location": f'{atm["city"]} ({atm["site_type"]})',
            "cash_left": atm["cash_left"],
            "add_cash": max(0, round(atm["atm_capacity"] * 0.9 - atm["cash_left"])),
            "risk_level": atm["risk_level"],
            "predicted_demand": atm["expected_demand"],
        }
        for atm in DEMO_ATMS
    ]


@router.get("/plan/route")
def get_demo_route():
    stops = [atm for atm in DEMO_ATMS if atm["risk_level"] in ("high", "medium")]
    steps = [{"step": 1, "title": "Start at Central Cash Depot", "atm_id": None,
              "location": "Demo depot", "leg_distance_km": 0.0}]
    for index, atm in enumerate(stops, start=2):
        steps.append({
            "step": index,
            "title": f'{atm["atm_id"]} - {atm["city"]} ({atm["site_type"]})',
            "atm_id": atm["atm_id"],
            "location": atm["city"],
            "leg_distance_km": round(8.5 + index * 2.1, 1),
        })
    steps.append({
        "step": len(steps) + 1, "title": "Return to Central Cash Depot",
        "atm_id": None, "location": "Demo depot", "leg_distance_km": 12.4,
    })
    return {
        "route": ["Depot"] + [atm["atm_id"] for atm in stops] + ["Depot"],
        "steps": steps,
        "total_distance_km": 68.4,
        "estimated_time_mins": 172,
        "atms_count": len(stops),
    }


@router.get("/model/metrics")
def get_demo_model_metrics():
    return {
        "model_name": "Gradient Boosting Regressor (demo)",
        "model_accuracy": 47.34,
        "forecast_accuracy": 90.2,
        "cash_out_reduced": 76.4,
        "target_accuracy": "85%",
        "target_cash_out": "70%",
        "test_mape": 0.098,
        "trained_at": "Sample evaluation",
    }


@router.get("/alerts")
def get_demo_alerts():
    now = date.today().isoformat()
    return [
        {
            "id": index,
            "atm_id": atm["atm_id"],
            "message": f'{atm["atm_id"]} ({atm["city"]}) sample alert: {atm["risk_level"]} cash risk.',
            "risk_level": atm["risk_level"],
            "cash_left": atm["cash_left"],
            "predicted_runout_days": round(atm["cash_left"] / atm["expected_demand"], 1),
            "created_at": now,
        }
        for index, atm in enumerate(DEMO_ATMS, start=1)
        if atm["risk_level"] in ("high", "medium")
    ]


@router.get("/atms")
def get_demo_atms():
    return DEMO_ATMS


@router.get("/forecast/atm/{atm_id}")
def get_demo_atm_forecast(atm_id: str, days: int = Query(7, ge=1, le=30)):
    atm = next((item for item in DEMO_ATMS if item["atm_id"] == atm_id), None)
    if atm is None:
        raise HTTPException(status_code=404, detail="Demo ATM not found.")

    forecasts = []
    cash_left = float(atm["cash_left"])
    for offset in range(days):
        demand = round(atm["expected_demand"] * (0.94 + (offset % 4) * 0.04), 2)
        cash_left = max(0, cash_left - demand)
        days_left = cash_left / demand if demand else 0
        forecasts.append({
            "date": (date.today() + timedelta(days=offset)).isoformat(),
            "day_name": (date.today() + timedelta(days=offset)).strftime("%a"),
            "predicted_demand": demand,
            "projected_cash_left": round(cash_left, 2),
            "risk_level": "high" if days_left <= 1 else "medium" if days_left <= 3 else "normal",
        })
    return {
        "atm_id": atm["atm_id"],
        "city": atm["city"],
        "atm_capacity": atm["atm_capacity"],
        "current_cash": atm["cash_left"],
        "forecasts": forecasts,
    }


@router.get("/forecast/region")
def get_demo_region_forecast(region: str = Query("All")):
    selected = [atm for atm in DEMO_ATMS if region == "All" or atm["region"] == region]
    if not selected:
        raise HTTPException(status_code=404, detail="Demo region not found.")
    return {
        "region": region,
        "atm_count": len(selected),
        "average_daily_demand": round(sum(atm["expected_demand"] for atm in selected) / len(selected), 2),
        "at_risk": sum(atm["risk_level"] == "high" for atm in selected),
        "locations": [
            {"atm_id": atm["atm_id"], "city": atm["city"], "predicted_demand": atm["expected_demand"],
             "cash_left": atm["cash_left"], "risk_level": atm["risk_level"]}
            for atm in selected
        ],
    }


@router.get("/analytics")
def get_demo_analytics(days: str = Query("30", alias="range", pattern="^(7|30|90)$")):
    return {"range": int(days), **_series(int(days))}
