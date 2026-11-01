from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, EmailStr

# Auth Schemas
class UserRegister(BaseModel):
    """Payload for user registration."""
    email: EmailStr
    full_name: str
    password: str

class UserLogin(BaseModel):
    """Payload for user sign in."""
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """User profile details sent in responses."""
    id: int
    email: str
    full_name: str

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    """JWT authorization token returned upon login."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Dashboard Schemas
class KPIResponse(BaseModel):
    """Key performance indicators for ATM cash operations."""
    avg_daily_demand_lakhs: float
    atms_at_risk: int
    refills_planned_week: int
    forecast_accuracy: float

class DemandChartResponse(BaseModel):
    """Actual vs forecasted cash demand series."""
    range: str
    x: List[str]
    actual: List[Optional[float]]
    forecast: List[Optional[float]]

class RefillATM(BaseModel):
    """ATM needing cash replenishment."""
    atm_id: str
    location: str
    cash_left: float
    predicted_out: str
    risk_level: str

# Replenishment Plan Schemas
class PlanItem(BaseModel):
    """Per-ATM refill recommendation and risk assessment."""
    atm_id: str
    location: str
    cash_left: float
    add_cash: float
    risk_level: str  # 'normal', 'medium', 'high'
    predicted_demand: float

class RouteRequest(BaseModel):
    """Optional payload to select specific ATMs for route optimization."""
    atm_ids: Optional[List[str]] = None

class RouteStep(BaseModel):
    """Single leg in the optimized replenishment journey."""
    step: int
    title: str
    atm_id: Optional[str] = None
    location: Optional[str] = None
    leg_distance_km: float

class RouteResponse(BaseModel):
    """OR-Tools optimized replenishment journey."""
    route: List[str]
    steps: List[RouteStep]
    total_distance_km: float
    estimated_time_mins: int
    atms_count: int

# Model & Alerts Schemas
class ModelMetrics(BaseModel):
    """Performance metrics from model evaluation."""
    model_name: str
    model_accuracy: float
    forecast_accuracy: float
    cash_out_reduced: float
    target_accuracy: str
    target_cash_out: str
    test_mape: float
    trained_at: str

class AlertItem(BaseModel):
    """Individual predictive alert for cash-out risk."""
    id: int
    atm_id: str
    message: str
    risk_level: str
    cash_left: float
    predicted_runout_days: float
    created_at: str

    class Config:
        from_attributes = True
