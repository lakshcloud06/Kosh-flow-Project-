from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    """User account table for authentication and profile."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ATM(Base):
    """ATM metadata and latest operational status."""
    __tablename__ = "atms"

    id = Column(String(50), primary_key=True, index=True)
    city = Column(String(100), nullable=False)
    location_type = Column(String(50), nullable=True)
    site_type = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    atm_capacity = Column(Float, nullable=False, default=2000000.0)
    nearby_atm_count = Column(Integer, default=1)
    current_cash = Column(Float, default=0.0)
    status = Column(String(50), default="active")

    records = relationship("DemandRecord", back_populates="atm", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="atm", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="atm", cascade="all, delete-orphan")

class DemandRecord(Base):
    """Daily historical demand and operational records for ATMs."""
    __tablename__ = "demand_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    atm_id = Column(String(50), ForeignKey("atms.id"), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    withdrawal_amount = Column(Float, nullable=True)
    no_of_withdrawals = Column(Float, nullable=True)
    deposit_amount = Column(Float, default=0.0)
    no_of_deposits = Column(Integer, default=0)
    balance_opening = Column(Float, default=0.0)
    balance_closing = Column(Float, default=0.0)
    cash_replenished = Column(Float, default=0.0)
    downtime_hours = Column(Float, default=0.0)
    cash_out_flag = Column(Integer, default=0)
    is_holiday = Column(Float, default=0.0)
    is_festival = Column(Integer, default=0)
    holiday_name = Column(String(100), nullable=True)
    is_salary_day = Column(Integer, default=0)
    temperature = Column(Float, nullable=True)
    rainfall = Column(Float, nullable=True)
    footfall_index = Column(Float, nullable=True)
    upi_national_monthly_txn_bn = Column(Float, nullable=True)
    upi_txn_count_area = Column(Float, nullable=True)
    upi_share_pct = Column(Float, nullable=True)

    atm = relationship("ATM", back_populates="records")

class Forecast(Base):
    """Model predictions for ATM cash demand."""
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    atm_id = Column(String(50), ForeignKey("atms.id"), index=True, nullable=False)
    forecast_date = Column(Date, index=True, nullable=False)
    predicted_demand = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    atm = relationship("ATM", back_populates="forecasts")

class Alert(Base):
    """Predictive alerts generated for low cash or impending cash-out."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    atm_id = Column(String(50), ForeignKey("atms.id"), index=True, nullable=False)
    message = Column(String(255), nullable=False)
    risk_level = Column(String(50), nullable=False)  # 'high', 'medium', 'normal'
    cash_left = Column(Float, default=0.0)
    predicted_runout_days = Column(Float, default=1.0)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    atm = relationship("ATM", back_populates="alerts")
