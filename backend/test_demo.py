import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.demo_router import router


class PublicDemoRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    def test_demo_reads_are_public_and_use_sample_records(self):
        response = self.client.get("/demo/atms")
        self.assertEqual(response.status_code, 200)
        atms = response.json()
        self.assertTrue(atms)
        self.assertTrue(all(atm["atm_id"].startswith("DEMO-") for atm in atms))

    def test_dashboard_and_analytics_ranges_return_consistent_series(self):
        dashboard = self.client.get("/demo/dashboard/demand", params={"range": "14"})
        analytics = self.client.get("/demo/analytics", params={"range": "90"})
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(len(dashboard.json()["x"]), 14)
        self.assertEqual(analytics.status_code, 200)
        self.assertEqual(len(analytics.json()["x"]), 90)

    def test_forecast_does_not_expose_unknown_atms(self):
        response = self.client.get("/demo/forecast/atm/REAL-ATM-001")
        self.assertEqual(response.status_code, 404)

    def test_demo_routes_have_no_write_methods(self):
        response = self.client.post("/demo/plan/route", json={})
        self.assertEqual(response.status_code, 405)


if __name__ == "__main__":
    unittest.main()
