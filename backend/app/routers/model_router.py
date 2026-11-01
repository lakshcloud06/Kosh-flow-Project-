import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from app.schemas import ModelMetrics
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/model", tags=["Model"])

# Written by 1_eda_clean_train.py - the single source of truth for every model number
METRICS_FILE = Path(__file__).resolve().parent.parent.parent / "outputs" / "metrics.json"


@router.get("/metrics", response_model=ModelMetrics)
def get_model_metrics(current_user: User = Depends(get_current_user)):
    """Model accuracy, forecast accuracy and cash-out metric, all MEASURED on the last 90 days of data."""
    if not METRICS_FILE.exists():
        raise HTTPException(status_code=503, detail="metrics.json not found. Run 1_eda_clean_train.py first.")
    m = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    return {
        "model_name": m["model_name"],
        "model_accuracy": m["model_accuracy"],           # R-squared of the forecast on unseen days
        "forecast_accuracy": m["forecast_accuracy"],     # 100 - weighted error, same value as the dashboard card
        "cash_out_reduced": m["cash_out_reduced"],       # share of real cash-outs warned about in advance (see cash_out_basis)
        "target_accuracy": m["target_accuracy"],
        "target_cash_out": m["target_cash_out"],
        "test_mape": m["test_mape"],
        "trained_at": m["trained_at"],
    }
