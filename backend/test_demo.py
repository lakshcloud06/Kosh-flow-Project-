import unittest
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.routers.dataset_router import router as dataset_router
from app.routers.demo_router import router as demo_router


class DatasetApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.session_factory = sessionmaker(bind=cls.engine)
        cls._create_dataset()

        app = FastAPI()
        app.include_router(dataset_router)
        app.include_router(demo_router)

        def get_test_db():
            with cls.session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = get_test_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    @classmethod
    def _create_dataset(cls):
        with cls.engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE ds_atms (atm_id TEXT PRIMARY KEY, city TEXT, "
                "location_type TEXT, site_type TEXT, latitude FLOAT, longitude FLOAT, "
                "atm_capacity FLOAT, nearby_atm_count INTEGER)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE ds_demand_records (atm_id TEXT, date DATE, "
                "withdrawal_amount FLOAT, cash_replenished FLOAT, balance_closing FLOAT, "
                "temperature FLOAT, rainfall FLOAT, footfall_index FLOAT, "
                "upi_share_pct FLOAT, is_holiday INTEGER, is_festival INTEGER)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE ds_forecasts (atm_id TEXT, date DATE, "
                "actual_amount FLOAT, forecast_amount FLOAT)"
            )
            connection.execute(text(
                "INSERT INTO ds_atms VALUES "
                "('ATM001', 'Mumbai', 'Metro', 'Branch', 19.0388, 72.89251, 2500000, 1)"
            ))
            for offset in range(8):
                record_date = date(2025, 12, 24) + timedelta(days=offset)
                withdrawal = 100000 + offset * 1000
                connection.execute(text(
                    "INSERT INTO ds_demand_records VALUES "
                    "(:atm_id, :date, :withdrawal, :replenished, :cash, "
                    ":temperature, :rainfall, :footfall, :upi, 0, 0)"
                ), {
                    "atm_id": "ATM001",
                    "date": record_date,
                    "withdrawal": withdrawal,
                    "replenished": 50000,
                    "cash": 800000 - offset * 50000,
                    "temperature": 25,
                    "rainfall": 0,
                    "footfall": 50,
                    "upi": 95,
                })
                connection.execute(text(
                    "INSERT INTO ds_forecasts VALUES "
                    "(:atm_id, :date, :actual, :forecast)"
                ), {
                    "atm_id": "ATM001",
                    "date": record_date,
                    "actual": withdrawal,
                    "forecast": withdrawal * 1.05,
                })

    def test_api_summary_filters_and_history_use_database_records(self):
        summary = self.client.get("/api/dashboard/summary")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["total_atms"], 1)
        self.assertEqual(summary.json()["total_records"], 8)
        self.assertEqual(summary.json()["date_start"], "2025-12-24")
        self.assertEqual(summary.json()["date_end"], "2025-12-31")

        atms = self.client.get("/api/atms")
        self.assertEqual(atms.status_code, 200)
        self.assertEqual(atms.json()[0]["atm_id"], "ATM001")

        analytics = self.client.get(
            "/api/analytics",
            params={"group_by": "date", "start_date": "2025-12-28", "end_date": "2025-12-31"},
        )
        self.assertEqual(analytics.status_code, 200)
        self.assertEqual(len(analytics.json()["data"]), 4)
        self.assertIsNotNone(analytics.json()["data"][0]["predicted_demand"])

        history = self.client.get("/api/atms/ATM001/history")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["data"]), 8)

    def test_public_demo_reads_dataset_and_model_forecasts(self):
        atms = self.client.get("/demo/atms")
        self.assertEqual(atms.status_code, 200)
        self.assertEqual(atms.json()[0]["atm_id"], "ATM001")

        forecast = self.client.get("/api/forecast", params={"atm_id": "ATM001", "days": 7})
        self.assertEqual(forecast.status_code, 200)
        self.assertEqual(len(forecast.json()["items"]), 7)
        self.assertTrue(all(item["predicted_demand"] >= 0 for item in forecast.json()["items"]))

        demo_analytics = self.client.get("/demo/analytics", params={"range": "7"})
        self.assertEqual(demo_analytics.status_code, 200)
        self.assertEqual(len(demo_analytics.json()["x"]), 7)

    def test_unknown_atm_and_write_methods_are_rejected(self):
        unknown = self.client.get("/api/atms/UNKNOWN/history")
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(self.client.post("/api/forecast").status_code, 405)
        self.assertEqual(self.client.post("/demo/plan/route").status_code, 405)


if __name__ == "__main__":
    unittest.main()
