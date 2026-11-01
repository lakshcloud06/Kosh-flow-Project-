from datetime import date, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ATM, DemandRecord
from app.auth import get_current_user
from app.services.forecast_service import predict_atm_demand, evaluate_risk_level

router = APIRouter(prefix="/forecast", tags=["Forecast"])

@router.get("/atm/{atm_id}")
def get_atm_forecast(
    atm_id: str,
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate multi-day cash demand forecast for a specific ATM."""
    atm = db.query(ATM).filter(ATM.id == atm_id).first()
    if not atm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ATM '{atm_id}' was not found."
        )

    today = date.today()
    forecasts = []
    cumulative_cash = float(atm.current_cash)

    for i in range(days):
        forecast_date = today + timedelta(days=i)
        pred = predict_atm_demand(
            atm.id, atm.city, atm.location_type or "Metro",
            atm.atm_capacity, atm.nearby_atm_count, forecast_date
        )
        cumulative_cash = max(0.0, cumulative_cash - pred)
        risk, days_left = evaluate_risk_level(cumulative_cash, pred)

        forecasts.append({
            "date": forecast_date.isoformat(),
            "day_name": forecast_date.strftime("%a"),
            "predicted_demand": pred,
            "projected_cash_left": round(cumulative_cash, 2),
            "risk_level": risk
        })

    return {
        "atm_id": atm.id,
        "city": atm.city,
        "atm_capacity": atm.atm_capacity,
        "current_cash": atm.current_cash,
        "forecasts": forecasts
    }
