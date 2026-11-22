from datetime import date, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ATM, DemandRecord
from app.auth import get_current_user
from app.services.forecast_service import (
    ModelUnavailableError,
    predict_atm_demand,
    evaluate_risk_level,
)

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
    history = db.query(DemandRecord).filter(
        DemandRecord.atm_id == atm_id
    ).order_by(DemandRecord.date.desc()).limit(30).all()
    history.reverse()
    if len(history) < 7:
        raise HTTPException(
            status_code=422,
            detail=f"ATM '{atm_id}' has fewer than seven historical records for inference.",
        )
    if any(record.withdrawal_amount is None for record in history):
        raise HTTPException(status_code=422, detail="Recent withdrawal history is incomplete.")
    history_values = [float(record.withdrawal_amount) for record in history]
    latest_record = history[-1]
    model_features = (
        latest_record.temperature,
        latest_record.rainfall,
        latest_record.footfall_index,
        latest_record.upi_share_pct,
    )
    if any(value is None for value in model_features):
        raise HTTPException(status_code=422, detail="Recent historical model features are incomplete.")
    if not atm.location_type or atm.atm_capacity is None or atm.nearby_atm_count is None:
        raise HTTPException(status_code=422, detail="ATM model metadata is incomplete.")

    for i in range(days):
        forecast_date = today + timedelta(days=i)
        recent_lags = {
            "lag_1": history_values[-1],
            "lag_7": history_values[-7],
            "roll_mean_7": sum(history_values[-7:]) / 7,
            "temperature": float(latest_record.temperature),
            "rainfall": float(latest_record.rainfall),
            "footfall_index": float(latest_record.footfall_index),
            "upi_share_pct": float(latest_record.upi_share_pct),
            "is_holiday": 0,
            "is_festival": 0,
        }
        try:
            pred = predict_atm_demand(
                atm.id, atm.city, atm.location_type,
                atm.atm_capacity, atm.nearby_atm_count, forecast_date, recent_lags
            )
        except ModelUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        cumulative_cash = max(0.0, cumulative_cash - pred)
        risk, days_left = evaluate_risk_level(cumulative_cash, pred)

        forecasts.append({
            "date": forecast_date.isoformat(),
            "day_name": forecast_date.strftime("%a"),
            "predicted_demand": pred,
            "projected_cash_left": round(cumulative_cash, 2),
            "risk_level": risk
        })
        history_values.append(pred)

    return {
        "atm_id": atm.id,
        "city": atm.city,
        "atm_capacity": atm.atm_capacity,
        "current_cash": atm.current_cash,
        "forecasts": forecasts
    }
