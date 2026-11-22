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
from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    text,
)
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
database_url = os.getenv("DB_URL_OVERRIDE") or url
connect_args = {}
if ssl_ca and not str(database_url).startswith("sqlite:"):
    ssl_ca = ssl_ca if os.path.isabs(ssl_ca) else os.path.join(BASE, ssl_ca)
    if not os.path.exists(ssl_ca):
        raise SystemExit(f"Certificate file not found: {ssl_ca}")
    connect_args = {"ssl": {"ca": ssl_ca}}
engine = create_engine(database_url, connect_args=connect_args)   # DB_URL_OVERRIDE is only for testing

if not os.path.exists(os.path.join(BASE, "outputs", "cleaned_data.csv")):
    raise SystemExit("outputs/cleaned_data.csv not found. Run 1_eda_clean_train.py first and wait until it prints Done.")
clean = pd.read_csv(os.path.join(BASE, "outputs", "cleaned_data.csv"), parse_dates=["date"])
fc = pd.read_csv(os.path.join(BASE, "outputs", "test_forecasts.csv"), parse_dates=["date"])
clean["date"] = clean["date"].dt.date
fc["date"] = fc["date"].dt.date

# NOTE: tables start with "ds_" (dataset) so they never clash with the backend's own tables (atms, alerts, users...)
# Table 1: one row per ATM (static details)
atm_cols = ["atm_id", "city", "location_type", "site_type", "latitude", "longitude", "atm_capacity", "nearby_atm_count"]
atms = clean[atm_cols].drop_duplicates("atm_id")
# Table 2: one row per ATM per day
records = clean.drop(columns=["city", "location_type", "site_type", "latitude", "longitude",
                              "atm_capacity", "nearby_atm_count"])

def _column_type(name, dtype):
    if name == "date":
        return Date()
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return DateTime()
    if pd.api.types.is_integer_dtype(dtype):
        return BigInteger()
    if pd.api.types.is_float_dtype(dtype):
        return Float()
    return String(255)


def load_table(df, name, key_columns):
    """Create missing dataset tables and insert only unseen natural keys."""
    allowed_tables = {"ds_atms", "ds_demand_records", "ds_forecasts"}
    if name not in allowed_tables:
        raise ValueError(f"Refusing to write outside dataset tables: {name}")

    inspector = inspect(engine)
    if not inspector.has_table(name):
        columns = [
            Column(
                column,
                _column_type(column, dtype),
                primary_key=column in key_columns,
                nullable=column not in key_columns,
            )
            for column, dtype in df.dtypes.items()
        ]
        Table(name, MetaData(), *columns).create(engine)
    else:
        existing_columns = {column["name"] for column in inspector.get_columns(name)}
        missing_columns = set(df.columns) - existing_columns
        if missing_columns:
            raise RuntimeError(
                f"Existing table {name} is missing required columns: "
                f"{', '.join(sorted(missing_columns))}"
            )

    if engine.dialect.name == "mysql":
        current_inspector = inspect(engine)
        indexes = current_inspector.get_indexes(name)
        natural_key_exists = any(
            index.get("unique")
            and set(index.get("column_names") or []) == set(key_columns)
            for index in indexes
        )
        if not natural_key_exists:
            column_types = {
                column["name"]: str(column["type"]).upper()
                for column in current_inspector.get_columns(name)
            }
            key_sql = ", ".join(
                f"`{column}`(50)" if column == "atm_id"
                and "TEXT" in column_types[column]
                else f"`{column}`"
                for column in key_columns
            )
            with engine.connect() as connection:
                duplicate_row = connection.execute(text(
                    f"SELECT 1 FROM `{name}` GROUP BY "
                    f"{', '.join(f'`{column}`' for column in key_columns)} "
                    "HAVING COUNT(*) > 1 LIMIT 1"
                )).first()
            if duplicate_row:
                raise RuntimeError(
                    f"Cannot guarantee idempotent imports: {name} has duplicate natural keys."
                )
            index_name = f"uq_{name}_{'_'.join(key_columns)}"
            with engine.begin() as connection:
                connection.exec_driver_sql(
                    f"CREATE UNIQUE INDEX `{index_name}` ON `{name}` ({key_sql})"
                )

    columns_sql = ", ".join(f"`{column}`" for column in df.columns)
    values_sql = ", ".join(f":{column}" for column in df.columns)
    insert_prefix = "INSERT IGNORE" if engine.dialect.name == "mysql" else "INSERT OR IGNORE"
    statement = text(f"{insert_prefix} INTO `{name}` ({columns_sql}) VALUES ({values_sql})")

    records_to_insert = (
        df.astype(object)
        .where(pd.notna(df), None)
        .to_dict(orient="records")
    )
    with engine.begin() as connection:
        for offset in range(0, len(records_to_insert), 1000):
            connection.execute(statement, records_to_insert[offset:offset + 1000])


load_table(atms, "ds_atms", ["atm_id"])
load_table(records, "ds_demand_records", ["atm_id", "date"])
forecasts = fc.rename(columns={"withdrawal_amount": "actual_amount", "forecast": "forecast_amount"})
load_table(forecasts, "ds_forecasts", ["atm_id", "date"])

with engine.connect() as connection:
    for table_name, source in (
        ("ds_atms", atms),
        ("ds_demand_records", records),
        ("ds_forecasts", forecasts),
    ):
        actual = connection.execute(text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar_one()
        print(f"{table_name}: source rows={len(source)}, database rows={actual}")
        if actual < len(source):
            raise RuntimeError(
                f"{table_name} contains fewer rows than the source dataset after import."
            )
print("Dataset import completed without deleting or replacing existing rows.")
