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
# Cloud databases such as Aiven need a secure (SSL) connection: set DB_SSL_CA to the certificate file path
ssl_ca = os.getenv("DB_SSL_CA")
connect_args = {}
if ssl_ca:
    ssl_ca = ssl_ca if os.path.isabs(ssl_ca) else os.path.join(BASE, ssl_ca)
    if not os.path.exists(ssl_ca):
        raise SystemExit(f"Certificate file not found: {ssl_ca}")
    connect_args = {"ssl": {"ca": ssl_ca}}
engine = create_engine(os.getenv("DB_URL_OVERRIDE", url), connect_args=connect_args)   # DB_URL_OVERRIDE is only for testing

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

def sql_type(dtype):
    """Pick a MySQL column type that matches a pandas column."""
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "DATETIME"
    if pd.api.types.is_integer_dtype(dtype):
        return "BIGINT"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE"
    return "VARCHAR(255)"


def load_table(df, name, key=None):
    """
    Create the table WITH a primary key (cloud databases such as Aiven refuse tables without one),
    then insert the rows. key = existing column to use as primary key; otherwise an auto id column is added.
    """
    if engine.dialect.name != "mysql":                       # only used by tests with SQLite
        df.to_sql(name, engine, if_exists="replace", index=False, chunksize=2000)
        return
    cols = [f"`{c}` {sql_type(t)}" for c, t in df.dtypes.items()]
    if key:
        cols = [c.replace("VARCHAR(255)", "VARCHAR(50) NOT NULL") if c.startswith(f"`{key}`") else c for c in cols]
        cols.append(f"PRIMARY KEY (`{key}`)")
    else:
        cols.insert(0, "`id` BIGINT NOT NULL AUTO_INCREMENT")
        cols.append("PRIMARY KEY (`id`)")
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS `{name}`"))
        conn.execute(text(f"CREATE TABLE `{name}` ({', '.join(cols)})"))
    df.to_sql(name, engine, if_exists="append", index=False, chunksize=2000)


load_table(atms, "ds_atms", key="atm_id")
load_table(records, "ds_demand_records")
load_table(fc.rename(columns={"withdrawal_amount": "actual_amount", "forecast": "forecast_amount"}), "ds_forecasts")

with engine.connect() as c:
    for t in ["ds_atms", "ds_demand_records", "ds_forecasts"]:
        print(t, "rows:", c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar())
print("Data loaded into MySQL.")
