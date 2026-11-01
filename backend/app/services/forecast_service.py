from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
import joblib
import pandas as pd
import numpy as np

# Cache loaded model bundle in memory
_model_bundle = None

def get_model_bundle():
    """Load the trained machine learning model bundle and feature encoders."""
    global _model_bundle
    if _model_bundle is None:
        model_path = Path(__file__).resolve().parent.parent.parent / "ml" / "model.joblib"
        if not model_path.exists():
            # Fallback path if run from project root
            model_path = Path("backend/ml/model.joblib")
        if model_path.exists():
            _model_bundle = joblib.load(model_path)
    return _model_bundle

def predict_atm_demand(
    atm_id: str,
    city: str,
    location_type: str,
    atm_capacity: float,
    nearby_atm_count: int,
    target_date: date,
    recent_lags: Optional[Dict[str, float]] = None
) -> float:
    """Predict cash demand (withdrawal amount in INR) for a given ATM and date."""
    bundle = get_model_bundle()
    if bundle is None:
        # Fallback heuristic if model file is not found
        return round(float(atm_capacity) * 0.28, 2)

    model = bundle["model"]
    encoders = bundle["encoders"]

    atm_categories = encoders.get("atm_categories", {})
    city_categories = encoders.get("city_categories", {})
    loc_categories = encoders.get("loc_categories", {})
    median_demand = encoders.get("median_demand", 465000.0)

    atm_code = atm_categories.get(atm_id, 0)
    city_code = city_categories.get(city.title(), 0)
    loc_code = loc_categories.get(location_type.title(), 0)

    dt = pd.to_datetime(target_date)
    day_of_week = dt.day_of_week
    is_weekend = 1 if day_of_week in [5, 6] else 0
    day = dt.day
    month = dt.month

    # Check for salary days (1st-5th of month)
    is_salary_day = 1 if day in [1, 2, 3, 4, 5, 30, 31] else 0

    lags = recent_lags or {}
    lag_1 = lags.get("lag_1", median_demand)
    lag_7 = lags.get("lag_7", median_demand)
    roll_mean_7 = lags.get("roll_mean_7", median_demand)

    features = [
        atm_code,
        city_code,
        loc_code,
        float(atm_capacity),
        int(nearby_atm_count),
        day_of_week,
        is_weekend,
        day,
        month,
        0,  # is_holiday
        0,  # is_festival
        is_salary_day,
        28.0,  # default temperature
        0.0,   # rainfall
        55.0,  # default footfall index
        95.0,  # upi_share_pct
        float(lag_1),
        float(lag_7),
        float(roll_mean_7)
    ]

    features_df = pd.DataFrame([features], columns=bundle["feature_columns"])
    pred = model.predict(features_df)[0]
    return max(50000.0, round(float(pred), 2))

def evaluate_risk_level(cash_left: float, predicted_daily_demand: float) -> Tuple[str, float]:
    """
    Calculate risk level and days until cash-out.
    Risk level rule:
    - High: predicted run-out within 1 day (cash_left <= 1 * predicted_daily_demand)
    - Medium: predicted run-out within 2 to 3 days (cash_left <= 3 * predicted_daily_demand)
    - Normal: more than 3 days of cash buffer available.
    """
    if predicted_daily_demand <= 0:
        predicted_daily_demand = 300000.0

    days_left = round(cash_left / predicted_daily_demand, 1)

    if days_left <= 1.0:
        return "high", days_left
    elif days_left <= 3.0:
        return "medium", days_left
    else:
        return "normal", days_left

def compute_suggested_refill(atm_capacity: float, current_cash: float, risk_level: str) -> float:
    """Compute optimal cash addition amount to restore ATM to safety target capacity."""
    # Target safety fill is 90% of capacity
    target_fill = atm_capacity * 0.90
    needed = max(0.0, target_fill - current_cash)
    # Round up to nearest 50,000 INR
    rounded = math_ceil_50k(needed)
    return float(rounded)

def math_ceil_50k(val: float) -> int:
    """Round cash amount up to nearest ₹50,000 banknote denomination chunk."""
    unit = 50000
    if val <= 0:
        return 0
    return int((int(val) + unit - 1) // unit) * unit
