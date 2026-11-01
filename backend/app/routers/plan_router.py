from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import PlanItem, RouteResponse, RouteRequest
from app.auth import get_current_user
from app.services.forecast_service import compute_suggested_refill
from app.services import real_data
from app.services.route_service import optimize_refill_route

router = APIRouter(prefix="/plan", tags=["Replenishment Plan"])


@router.get("", response_model=List[PlanItem])
def get_replenishment_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refill recommendation for every ATM, from real cash and the model's forecast."""
    plan_items = []
    for r in real_data.atm_risk_table(db):
        add_cash = compute_suggested_refill(r["atm_capacity"], r["cash_left"], r["risk_level"])
        plan_items.append({
            "atm_id": r["atm_id"],
            "location": f"{r['city']} ({r['site_type']})",
            "cash_left": r["cash_left"],
            "add_cash": add_cash,
            "risk_level": r["risk_level"],
            "predicted_demand": r["expected_demand"]
        })

    # High risk first, then medium, then normal; biggest refill first inside each group
    priority = {"high": 0, "medium": 1, "normal": 2}
    plan_items.sort(key=lambda x: (priority.get(x["risk_level"], 2), -x["add_cash"]))
    return plan_items


@router.post("/route", response_model=RouteResponse)
def compute_route(
    payload: Optional[RouteRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """OR-Tools route (Depot -> ATMs -> Depot). Default stops: all High and Medium risk ATMs."""
    table = real_data.atm_risk_table(db)
    if payload and payload.atm_ids:
        chosen = [r for r in table if r["atm_id"] in payload.atm_ids]
    else:
        chosen = [r for r in table if r["risk_level"] in ("high", "medium")]

    atms_data = [{
        "atm_id": r["atm_id"],
        "city": r["city"],
        "site_type": r["site_type"],
        "location": f"{r['city']} ({r['site_type']})",
        "latitude": r["latitude"],
        "longitude": r["longitude"],
        "current_cash": r["cash_left"],
        "atm_capacity": r["atm_capacity"]
    } for r in chosen]

    return optimize_refill_route(atms_data)
