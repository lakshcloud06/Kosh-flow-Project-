"""
Koshflow - Step 1: EDA, cleaning and model training.
Run:  python 1_eda_clean_train.py ATM_cash_demand.csv
Creates: outputs/cleaned_data.csv, outputs/model.joblib, outputs/metrics.json,
         outputs/test_forecasts.csv and a few EDA charts (png).
"""
import sys, os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib
from sklearn.ensemble import HistGradientBoostingRegressor

# Everything is found relative to this script's own folder, so it works from any terminal folder
BASE = os.path.dirname(os.path.abspath(__file__))
CSV = sys.argv[1] if len(sys.argv) > 1 else "ATM_cash_demand.csv"
if not os.path.exists(CSV):
    CSV = os.path.join(BASE, CSV)
if not os.path.exists(CSV):
    raise SystemExit(f"CSV file not found: {CSV}\nPut ATM_cash_demand.csv in the same folder as this script, "
                     "or type its exact name after the script name.")
OUT = os.path.join(BASE, "outputs") + os.sep
os.makedirs(OUT, exist_ok=True)   # create the outputs folder if it does not exist

# ---------- 1. LOAD ----------
df = pd.read_csv(CSV)
print("Rows, columns:", df.shape)

# Dates come in two formats (2023-01-01 and 17/03/2023), so parse both.
iso = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
dmy = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")
df["date"] = iso.fillna(dmy)
df = df.dropna(subset=["date"])

# ---------- 2. EDA (before cleaning) ----------
print("\nMissing values per column:\n", df.isna().sum()[df.isna().sum() > 0])
print("Duplicate ATM+date rows:", df.duplicated(["atm_id", "date"]).sum())
print("City spellings before cleaning:", df["city"].nunique())
df.isna().sum()[df.isna().sum() > 0].sort_values().plot.barh(figsize=(7, 4), title="Missing values per column")
plt.tight_layout(); plt.savefig(OUT + "eda_missing.png"); plt.close()

# ---------- 3. CLEANING ----------
df = df.drop_duplicates(["atm_id", "date"]).sort_values(["atm_id", "date"]).reset_index(drop=True)

# Same word written many ways ("MUMBAI", "mumbai ", "Mumbai") -> one clean spelling
df["city"] = df["city"].str.strip().str.title()
df["location_type"] = df["location_type"].str.strip().str.title()
df["site_type"] = df["site_type"].fillna("Unknown")
df["holiday_name"] = df["holiday_name"].fillna("None")
df["is_holiday"] = df["is_holiday"].fillna(0)

# Impossible values become missing: negative withdrawals, temperature outside -5..55 C
df.loc[df["withdrawal_amount"] < 0, "withdrawal_amount"] = np.nan
df.loc[~df["temperature"].between(-5, 55), "temperature"] = np.nan

# Cap extreme spikes at the 99.5th percentile (e.g. 7.2M when normal max is ~1M)
cap = df["withdrawal_amount"].quantile(0.995)
df["withdrawal_amount"] = df["withdrawal_amount"].clip(upper=cap)

# Fill remaining gaps: first from the same ATM's neighbouring days, then ATM median
num_fill = ["withdrawal_amount", "no_of_withdrawals", "balance_closing", "cash_replenished",
            "temperature", "rainfall", "footfall_index", "upi_txn_count_area"]
for c in num_fill:
    df[c] = df.groupby("atm_id")[c].transform(lambda s: s.interpolate(limit_direction="both"))
    df[c] = df[c].fillna(df[c].median())
df.to_csv(OUT + "cleaned_data.csv", index=False)
print("Cities after cleaning:", df["city"].nunique())
print("Cleaned rows:", len(df), "| missing left:", int(df.isna().sum().sum()))

# ---------- 4. EDA (after cleaning) ----------
df.groupby("date")["withdrawal_amount"].sum().div(1e5).plot(figsize=(9, 3.5), title="Total daily withdrawals (Rs lakhs)")
plt.tight_layout(); plt.savefig(OUT + "eda_daily_demand.png"); plt.close()
df.groupby(df["date"].dt.day_name())["withdrawal_amount"].mean().div(1e5).plot.bar(title="Average withdrawal by weekday (Rs lakhs)")
plt.tight_layout(); plt.savefig(OUT + "eda_weekday.png"); plt.close()
df.groupby("location_type")["withdrawal_amount"].mean().div(1e5).plot.bar(title="Average withdrawal by location type (Rs lakhs)")
plt.tight_layout(); plt.savefig(OUT + "eda_location.png"); plt.close()

# ---------- 5. FEATURES ----------
# Only use things we would know BEFORE the day happens (no same-day balance/footfall -> no leakage).
df["day_of_week"] = df["date"].dt.dayofweek
df["month"] = df["date"].dt.month
df["day"] = df["date"].dt.day
df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
g = df.groupby("atm_id")["withdrawal_amount"]
df["lag_1"] = g.shift(1)
df["lag_7"] = g.shift(7)
df["roll_7"] = g.transform(lambda s: s.shift(1).rolling(7).mean())
df["roll_30"] = g.transform(lambda s: s.shift(1).rolling(30).mean())
df["atm_code"] = df["atm_id"].astype("category").cat.codes
df["loc_code"] = df["location_type"].astype("category").cat.codes
FEATURES = ["day_of_week", "month", "day", "is_weekend", "is_salary_day", "is_festival", "is_holiday",
            "temperature", "rainfall", "atm_capacity", "nearby_atm_count", "atm_code", "loc_code",
            "lag_1", "lag_7", "roll_7", "roll_30"]
data = df.dropna(subset=["lag_1", "lag_7", "roll_7", "roll_30"]).copy()   # keeps balance_opening and cash_out_flag for the evaluation

# ---------- 6. TRAIN / TEST (time based: last 90 days are the test) ----------
split = data["date"].max() - pd.Timedelta(days=90)
train, test = data[data["date"] <= split], data[data["date"] > split].copy()
model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.08, random_state=42)
model.fit(train[FEATURES], train["withdrawal_amount"])
test["forecast"] = model.predict(test[FEATURES])

# ---------- 7. METRICS ----------
err = (test["withdrawal_amount"] - test["forecast"]).abs()
mae = err.mean()
rmse = float(np.sqrt(((test["withdrawal_amount"] - test["forecast"]) ** 2).mean()))
accuracy = 100 * (1 - err.sum() / test["withdrawal_amount"].sum())      # 100 - WAPE
y, f = test["withdrawal_amount"], test["forecast"]
r2 = 1 - ((y - f) ** 2).sum() / ((y - y.mean()) ** 2).sum()            # model accuracy = R-squared (how much of the ups and downs the model explains)
mape = float((err[y > 0] / y[y > 0]).mean())

# Cash-out early warning: on a day where the ATM's OPENING balance is below the forecast demand,
# we warn "this ATM will run out today". Check it against the real cash_out_flag in the test period.
warn = test["balance_opening"] < test["forecast"]
real_out = test["cash_out_flag"] == 1
caught = int((warn & real_out).sum())
recall = 100 * caught / max(1, int(real_out.sum()))                    # share of real cash-outs that were warned about
precision = 100 * caught / max(1, int(warn.sum()))                     # share of warnings that were right

metrics = {"model_name": "Gradient Boosting Regressor (ATM Cash Forecaster)",
           "model_accuracy": round(float(r2) * 100, 2),
           "forecast_accuracy": round(float(accuracy), 2),
           "forecast_accuracy_pct": round(float(accuracy), 2),
           "cash_out_reduced": round(recall, 2),
           "cash_out_basis": "share of real cash-out days that the forecast warned about before the day (opening balance < forecast)",
           "warning_precision_pct": round(precision, 2),
           "cash_outs_in_test": int(real_out.sum()), "cash_outs_warned": caught,
           "target_accuracy": ">= 85%", "target_cash_out": ">= 70%",
           "test_mape": round(mape, 4),
           "mae_rupees": round(float(mae)), "rmse_rupees": round(rmse),
           "train_rows": len(train), "test_rows": len(test),
           "trained_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
           "features": FEATURES}
json.dump(metrics, open(OUT + "metrics.json", "w"), indent=2)
print("\nMetrics:", {k: v for k, v in metrics.items() if k not in ("features", "cash_out_basis")})

test[["atm_id", "date", "withdrawal_amount", "forecast"]].to_csv(OUT + "test_forecasts.csv", index=False)
joblib.dump({"model": model, "features": FEATURES}, OUT + "model.joblib")
daily = test.groupby("date")[["withdrawal_amount", "forecast"]].sum().div(1e5)
ax = daily["withdrawal_amount"].plot(figsize=(9, 3.5), color="#2563EB", label="Actual")
daily["forecast"].plot(ax=ax, color="#475569", linestyle="--", label="Forecast")
plt.title("Actual vs forecast (test period, Rs lakhs)"); plt.legend(); plt.tight_layout()
plt.savefig(OUT + "actual_vs_forecast.png"); plt.close()
print("Done. Files saved in the outputs/ folder.")
