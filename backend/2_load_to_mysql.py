"""
Koshflow - Step 2: load cleaned data + forecasts into MySQL.
1) Create an empty database in MySQL:   CREATE DATABASE koshflow;
2) Put your details in a file named .env next to this script:
      DB_HOST=localhost
      DB_PORT=3306
      DB_USER=root
      DB_PASSWORD=your_password
      DB_NAME=koshflow
3) Run:  python 2_load_to_mysql.py
Install once:  pip install pandas sqlalchemy pymysql python-dotenv
"""
import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Read the .env file that sits in the same folder as this script
BASE = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE, ".env")
if not os.path.exists(env_path):
    raise SystemExit(f"Could not find the .env file at: {env_path}\n"
                     "Make sure it is named exactly .env (not .env.txt) and is in the same folder as this script.")
load_dotenv(env_path)

# Stop early with a clear message if something is missing in .env
missing = [k for k in ["DB_USER", "DB_PASSWORD", "DB_NAME"] if not os.getenv(k)]
if missing:
    raise SystemExit(f"These values are empty or missing in your .env file: {', '.join(missing)}")

# URL.create handles special characters (like @ or #) in the password safely
url = URL.create("mysql+pymysql", username=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
                 host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", "3306")),
                 database=os.getenv("DB_NAME"))
engine = create_engine(os.getenv("DB_URL_OVERRIDE", url))   # DB_URL_OVERRIDE is only for testing

if not os.path.exists(os.path.join(BASE, "outputs", "cleaned_data.csv")):
    raise SystemExit("outputs/cleaned_data.csv not found. Run 1_eda_clean_train.py first and wait until it prints Done.")
clean = pd.read_csv(os.path.join(BASE, "outputs", "cleaned_data.csv"), parse_dates=["date"])
fc = pd.read_csv(os.path.join(BASE, "outputs", "test_forecasts.csv"), parse_dates=["date"])

# NOTE: tables start with "ds_" (dataset) so they never clash with the backend's own tables (atms, alerts, users...)
# Table 1: one row per ATM (static details)
atm_cols = ["atm_id", "city", "location_type", "site_type", "latitude", "longitude", "atm_capacity", "nearby_atm_count"]
atms = clean[atm_cols].drop_duplicates("atm_id")
# Table 2: one row per ATM per day
records = clean.drop(columns=["city", "location_type", "site_type", "latitude", "longitude",
                              "atm_capacity", "nearby_atm_count"])

atms.to_sql("ds_atms", engine, if_exists="replace", index=False)
records.to_sql("ds_demand_records", engine, if_exists="replace", index=False, chunksize=2000)
fc.rename(columns={"withdrawal_amount": "actual_amount", "forecast": "forecast_amount"}) \
  .to_sql("ds_forecasts", engine, if_exists="replace", index=False, chunksize=2000)

with engine.connect() as c:
    for t in ["ds_atms", "ds_demand_records", "ds_forecasts"]:
        print(t, "rows:", c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar())
print("Data loaded into MySQL.")
