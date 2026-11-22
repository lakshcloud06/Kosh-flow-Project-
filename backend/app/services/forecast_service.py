from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
import logging
import joblib
import pandas as pd

# Cache loaded model bundle in memory
_model_bundle = None
logger = logging.getLogger("koshflow.forecast")
MODEL_FEATURES = [
    "atm_code", "city_code", "loc_code", "atm_capacity", "nearby_atm_count",
    "day_of_week", "is_weekend", "day", "month", "is_holiday", "is_festival",
    "is_salary_day", "temperature", "rainfall", "footfall_index", "upi_share_pct",
    "lag_1", "lag_7", "roll_mean_7",
]


class ModelUnavailableError(RuntimeError):
    """Raised when the trained forecasting model cannot be used."""

def get_model_bundle():
    """Load the trained machine learning model bundle and feature encoders."""
    global _model_bundle
    if _model_bundle is None:
        model_path = Path(__file__).resolve().parent.parent.parent / "ml" / "model.joblib"
        if not model_path.is_file():
            raise ModelUnavailableError(f"Trained model file is missing: {model_path}")
        try:
            _model_bundle = joblib.load(model_path)
        except Exception as exc:
            logger.exception("Unable to load the trained forecasting model.")
            raise ModelUnavailableError("The trained forecasting model could not be loaded.") from exc

        required_keys = {"model", "encoders", "feature_columns"}
        if not required_keys.issubset(_model_bundle):
            _model_bundle = None
            raise ModelUnavailableError("The trained model bundle has an incompatible format.")
        if _model_bundle["feature_columns"] != MODEL_FEATURES:
            _model_bundle = None
            raise ModelUnavailableError("The trained model feature contract is incompatible.")
        expected_features = len(_model_bundle["feature_columns"])
        if getattr(_model_bundle["model"], "n_features_in_", None) != expected_features:
            _model_bundle = None
            raise ModelUnavailableError("The model feature count does not match its saved feature contract.")
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
    if recent_lags is None:
        raise ValueError("Recent dataset features are required for model inference.")

    model = bundle["model"]
    encoders = bundle["encoders"]

    atm_categories = encoders.get("atm_categories", {})
    city_categories = encoders.get("city_categories", {})
    loc_categories = encoders.get("loc_categories", {})
    if atm_id not in atm_categories:
        raise ValueError(f"ATM '{atm_id}' is not in the trained model's feature encoders.")
    if city.title() not in city_categories:
        raise ValueError(f"City '{city}' is not in the trained model's feature encoders.")
    if location_type.title() not in loc_categories:
        raise ValueError(f"Location type '{location_type}' is not in the trained model's feature encoders.")

    atm_code = atm_categories[atm_id]
    city_code = city_categories[city.title()]
    loc_code = loc_categories[location_type.title()]

    dt = pd.to_datetime(target_date)
    day_of_week = dt.day_of_week
    is_weekend = 1 if day_of_week in [5, 6] else 0
    day = dt.day
    month = dt.month

    # Check for salary days (1st-5th of month)
    is_salary_day = 1 if day in [1, 2, 3, 4, 5, 30, 31] else 0

    lags = recent_lags
    required_features = (
        "lag_1", "lag_7", "roll_mean_7",
        "temperature", "rainfall", "footfall_index", "upi_share_pct",
    )
    missing_features = [name for name in required_features if name not in lags or lags[name] is None]
    if missing_features:
        raise ValueError(f"Missing dataset inference features: {', '.join(missing_features)}")

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
        int(lags.get("is_holiday", 0)),
        int(lags.get("is_festival", 0)),
        is_salary_day,
        float(lags["temperature"]),
        float(lags["rainfall"]),
        float(lags["footfall_index"]),
        float(lags["upi_share_pct"]),
        float(lags["lag_1"]),
        float(lags["lag_7"]),
        float(lags["roll_mean_7"])
    ]

    features_df = pd.DataFrame([features], columns=bundle["feature_columns"])
    pred = model.predict(features_df)[0]
    return max(0.0, round(float(pred), 2))

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
