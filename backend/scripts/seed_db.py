import os
import sys
from pathlib import Path
from datetime import datetime, date
import pandas as pd
from sqlalchemy.orm import Session

# Add backend directory to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import engine, SessionLocal, init_db
from app.models import User, ATM, DemandRecord, Alert, Forecast
from app.auth import get_password_hash
from app.services.forecast_service import predict_atm_demand, evaluate_risk_level

def locate_csv() -> Path:
    """Find ATM_cash_demand.csv file."""
    candidates = [
        Path("ATM_cash_demand.csv"),
        Path(__file__).resolve().parent.parent.parent / "ATM_cash_demand.csv",
        Path(__file__).resolve().parent.parent / "ATM_cash_demand.csv",
        Path("c:/Users/laksh/Downloads/Kosh Flow/ATM_cash_demand.csv"),
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find ATM_cash_demand.csv")

def seed_database():
    """Seed database with demo user, ATM metadata, historical demand records, and alerts."""
    print("Initializing database tables...")
    init_db()

    db: Session = SessionLocal()
    try:
        # 1. Create Demo User
        demo_email = "demo@koshflow.com"
        existing_user = db.query(User).filter(User.email == demo_email).first()
        if not existing_user:
            demo_user = User(
                email=demo_email,
                full_name="Aditya Sharma",
                hashed_password=get_password_hash("password123")
            )
            db.add(demo_user)
            db.commit()
            print(f"Created demo user: {demo_email} (password: password123)")
        else:
            print(f"Demo user {demo_email} already exists.")

        # 2. Load CSV Data
        csv_file = locate_csv()
        print(f"Reading CSV data from: {csv_file}")
        df = pd.read_csv(csv_file)
        df["date"] = pd.to_datetime(df["date"], format="mixed")
        df = df.sort_values(["atm_id", "date"]).reset_index(drop=True)

        # 3. Seed ATMs
        print("Seeding ATM network nodes...")
        atm_grouped = df.groupby("atm_id")
        for atm_id, group in atm_grouped:
            latest_row = group.iloc[-1]
            existing_atm = db.query(ATM).filter(ATM.id == atm_id).first()

            # Sensible fallback for cash left: latest closing balance or 40% capacity
            latest_cash = float(latest_row["balance_closing"]) if pd.notnull(latest_row["balance_closing"]) else float(latest_row["atm_capacity"]) * 0.35
            # Ensure realistic variance so some ATMs are critical (< 1 day), some medium, some normal
            if atm_id in ["ATM005", "ATM006", "ATM007", "ATM009", "ATM014", "ATM023"]:
                latest_cash = float(latest_row["atm_capacity"]) * 0.12  # High risk (< 1 day cash)
            elif atm_id in ["ATM002", "ATM010", "ATM018", "ATM028"]:
                latest_cash = float(latest_row["atm_capacity"]) * 0.45  # Medium risk (2-3 days)

            city_clean = str(latest_row["city"]).strip().title()
            loc_clean = str(latest_row["location_type"]).strip().title()
            site_clean = str(latest_row["site_type"]).strip() if pd.notnull(latest_row["site_type"]) else "Branch"

            if not existing_atm:
                new_atm = ATM(
                    id=atm_id,
                    city=city_clean,
                    location_type=loc_clean,
                    site_type=site_clean,
                    latitude=float(latest_row["latitude"]),
                    longitude=float(latest_row["longitude"]),
                    atm_capacity=float(latest_row["atm_capacity"]),
                    nearby_atm_count=int(latest_row["nearby_atm_count"]),
                    current_cash=latest_cash,
                    status="active"
                )
                db.add(new_atm)
            else:
                existing_atm.city = city_clean
                existing_atm.current_cash = latest_cash
        db.commit()
        print(f"Seeded {len(atm_grouped)} ATMs.")

        # 4. Seed Historical Demand Records (up to 2000 most recent records for fast startup)
        records_count = db.query(DemandRecord).count()
        if records_count < 100:
            print("Seeding historical demand records...")
            records_to_insert = []
            # Take last 60 days per ATM to keep database light and responsive
            sample_df = df.groupby("atm_id").tail(60).copy()

            for _, row in sample_df.iterrows():
                withdrawal = float(row["withdrawal_amount"]) if pd.notnull(row["withdrawal_amount"]) and row["withdrawal_amount"] > 0 else 450000.0
                rec = DemandRecord(
                    atm_id=str(row["atm_id"]),
                    date=row["date"].date(),
                    withdrawal_amount=withdrawal,
                    no_of_withdrawals=float(row["no_of_withdrawals"]) if pd.notnull(row["no_of_withdrawals"]) else 180.0,
                    deposit_amount=float(row["deposit_amount"]) if pd.notnull(row["deposit_amount"]) else 0.0,
                    no_of_deposits=int(row["no_of_deposits"]) if pd.notnull(row["no_of_deposits"]) else 0,
                    balance_opening=float(row["balance_opening"]) if pd.notnull(row["balance_opening"]) else 1500000.0,
                    balance_closing=float(row["balance_closing"]) if pd.notnull(row["balance_closing"]) else 800000.0,
                    cash_replenished=float(row["cash_replenished"]) if pd.notnull(row["cash_replenished"]) else 0.0,
                    downtime_hours=float(row["downtime_hours"]) if pd.notnull(row["downtime_hours"]) else 0.0,
                    cash_out_flag=int(row["cash_out_flag"]) if pd.notnull(row["cash_out_flag"]) else 0,
                    is_holiday=float(row["is_holiday"]) if pd.notnull(row["is_holiday"]) else 0.0,
                    is_festival=int(row["is_festival"]) if pd.notnull(row["is_festival"]) else 0,
                    holiday_name=str(row["holiday_name"]) if pd.notnull(row["holiday_name"]) else None,
                    is_salary_day=int(row["is_salary_day"]) if pd.notnull(row["is_salary_day"]) else 0,
                    temperature=float(row["temperature"]) if pd.notnull(row["temperature"]) else 28.0,
                    rainfall=float(row["rainfall"]) if pd.notnull(row["rainfall"]) else 0.0,
                    footfall_index=float(row["footfall_index"]) if pd.notnull(row["footfall_index"]) else 50.0,
                    upi_national_monthly_txn_bn=float(row["upi_national_monthly_txn_bn"]) if pd.notnull(row["upi_national_monthly_txn_bn"]) else 8.04,
                    upi_txn_count_area=float(row["upi_txn_count_area"]) if pd.notnull(row["upi_txn_count_area"]) else 4000.0,
                    upi_share_pct=float(row["upi_share_pct"]) if pd.notnull(row["upi_share_pct"]) else 95.0
                )
                records_to_insert.append(rec)

            db.bulk_save_objects(records_to_insert)
            db.commit()
            print(f"Inserted {len(records_to_insert)} historical demand records.")
        else:
            print(f"Historical records already exist ({records_count} rows).")

        # 5. Generate Predictive Alerts
        db.query(Alert).delete()
        db.commit()

        target_date = date.today()
        atms = db.query(ATM).all()
        for atm in atms:
            pred = predict_atm_demand(
                atm.id, atm.city, atm.location_type or "Metro",
                atm.atm_capacity, atm.nearby_atm_count, target_date
            )
            risk, days_left = evaluate_risk_level(atm.current_cash, pred)
            if risk in ["high", "medium"]:
                if days_left <= 0.3:
                    msg = f"{atm.id} ({atm.city}) critical: predicted to run out in less than 6 hours."
                elif days_left <= 1.0:
                    msg = f"{atm.id} ({atm.city}) predicted to run out of cash tomorrow."
                else:
                    msg = f"{atm.id} ({atm.city}) cash buffer low: ~{days_left:.1f} days remaining."

                alert = Alert(
                    atm_id=atm.id,
                    message=msg,
                    risk_level=risk,
                    cash_left=atm.current_cash,
                    predicted_runout_days=days_left,
                    is_read=False,
                    created_at=datetime.utcnow()
                )
                db.add(alert)
        db.commit()
        print(f"Generated active alerts for network operations.")

        print("Database seeding completed successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
