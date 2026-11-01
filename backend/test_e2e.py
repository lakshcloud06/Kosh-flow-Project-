import sys
import httpx

# Ensure console output handles UTF-8 characters cleanly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def run_tests():
    client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

    print("\n========================================================")
    print("   KOSHFLOW END-TO-END SYSTEM INTEGRATION TEST SUITE")
    print("========================================================\n")

    # Test 1: Service Health
    r = client.get("/")
    assert r.status_code == 200
    print("[PASS] 1. Root & Health endpoint: 200 OK")

    # Test 2: Authentication
    r = client.post("/auth/login", json={"email": "demo@koshflow.com", "password": "password123"})
    assert r.status_code == 200
    data = r.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_name = data["user"]["full_name"]
    print(f"[PASS] 2. Login successful: Welcome {user_name}, JWT Bearer token received")

    # Test 3: Authenticated User Profile
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    print(f"[PASS] 3. /auth/me verified: {r.json()['email']}")

    # Test 4: Dashboard KPIs
    r = client.get("/dashboard/kpis", headers=headers)
    assert r.status_code == 200
    kpis = r.json()
    print(f"[PASS] 4. KPIs verified:")
    print(f"         - Average Daily Demand: INR {kpis['avg_daily_demand_lakhs']} Lakhs")
    print(f"         - ATMs at Risk: {kpis['atms_at_risk']}")
    print(f"         - Refills Planned this Week: {kpis['refills_planned_week']}")
    print(f"         - Forecast Accuracy: {kpis['forecast_accuracy']}%")

    # Test 5: Demand Series across all 4 time horizons
    for rng in ["1", "7", "14", "30"]:
        r = client.get(f"/dashboard/demand?range={rng}", headers=headers)
        assert r.status_code == 200
        chart_data = r.json()
        print(f"[PASS] 5. Demand range={rng}: {len(chart_data['x'])} points (x={chart_data['x'][:3]}...)")

    # Test 6: Refill ATMs
    r = client.get("/dashboard/refill-atms", headers=headers)
    assert r.status_code == 200
    refills = r.json()
    print(f"[PASS] 6. Refill ATMs: {len(refills)} machines requiring attention")
    print(f"         Top machine: {refills[0]['atm_id']} ({refills[0]['location']}) - Risk: {refills[0]['risk_level'].upper()}")

    # Test 7: Replenishment Plan
    r = client.get("/plan", headers=headers)
    assert r.status_code == 200
    plan = r.json()
    print(f"[PASS] 7. Replenishment Plan: {len(plan)} ATMs analyzed")
    print(f"         Sample recommendation: {plan[0]['atm_id']} add INR {plan[0]['add_cash']:,.0f}")

    # Test 8: Google OR-Tools Routing
    r = client.post("/plan/route", headers=headers, json={})
    assert r.status_code == 200
    route = r.json()
    print(f"[PASS] 8. Google OR-Tools Replenishment Route:")
    print(f"         - Total Distance: {route['total_distance_km']} km")
    print(f"         - Estimated Mission Time: {route['estimated_time_mins']} mins")
    print(f"         - Total Stops: {len(route['steps'])} stops starting and ending at Depot")

    # Test 9: Model Metrics & Targets
    r = client.get("/model/metrics", headers=headers)
    assert r.status_code == 200
    metrics = r.json()
    print(f"[PASS] 9. Model Metrics & Target Verification:")
    print(f"         - Model: {metrics['model_name']}")
    print(f"         - Forecast Accuracy: {metrics['forecast_accuracy']}% (Target >= 85.0%) -> MET!")
    print(f"         - Cash-Out Incidents Reduced: {metrics['cash_out_reduced']}% (Target >= 70.0%) -> MET!")
    assert metrics['forecast_accuracy'] >= 85.0, "Forecast accuracy requirement not met!"
    assert metrics['cash_out_reduced'] >= 70.0, "Cash-out reduction requirement not met!"

    # Test 10: Alerts for Notification Bar
    r = client.get("/alerts", headers=headers)
    assert r.status_code == 200
    alerts = r.json()
    print(f"[PASS] 10. Predictive Alerts: {len(alerts)} alerts active")
    print(f"          Latest: \"{alerts[0]['message']}\"")

    print("\n========================================================")
    print("   ALL 10/10 INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    print("========================================================\n")

if __name__ == "__main__":
    run_tests()
