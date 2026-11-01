import React, { useState, useEffect } from "react";
import api from "../api/client";
import {
  Truck,
  MapPin,
  Clock,
  Compass,
  ArrowRight,
  RotateCw,
  CheckCircle,
  AlertCircle
} from "lucide-react";

export default function PlanPage() {
  const [planItems, setPlanItems] = useState([]);
  const [routeData, setRouteData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [routeLoading, setRouteLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchPlan = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/plan");
      setPlanItems(res.data);
    } catch (err) {
      console.error("Failed to fetch plan:", err);
      setError("Unable to load replenishment plan from backend.");
    } finally {
      setLoading(false);
    }
  };

  const generateRoute = async () => {
    setRouteLoading(true);
    try {
      const res = await api.post("/plan/route", {});
      setRouteData(res.data);
    } catch (err) {
      console.error("Failed to generate route:", err);
      setError("Routing optimization engine failed. Ensure Google OR-Tools is available.");
    } finally {
      setRouteLoading(false);
    }
  };

  useEffect(() => {
    fetchPlan();
    // Auto generate initial route
    generateRoute();
  }, []);

  const formatLakhs = (amount) => {
    if (!amount) return "₹0.00";
    return `₹${(amount / 100000).toFixed(2)} L`;
  };

  if (loading) {
    return (
      <div className="page-loader">
        <div className="spinner"></div>
        <p>Calculating dynamic replenishment schedules...</p>
      </div>
    );
  }

  return (
    <div className="plan-page">
      {/* Header and Actions */}
      <div className="page-header">
        <div>
          <h1 className="welcome-text">Replenishment Plan</h1>
          <p className="welcome-subtext">
            AI-driven cash replenishment amounts and OR-Tools optimal route scheduling.
          </p>
        </div>

        <div className="plan-actions">
          {/* Legend of risk badges */}
          <div className="risk-legend">
            <span className="legend-label">Risk Levels:</span>
            <span className="risk-badge badge-normal">Normal</span>
            <span className="risk-badge badge-medium">Medium</span>
            <span className="risk-badge badge-high">High</span>
          </div>

          <button
            type="button"
            className="btn btn-teal generate-route-btn"
            onClick={generateRoute}
            disabled={routeLoading}
          >
            {routeLoading ? (
              <>
                <RotateCw size={16} className="spin-icon" />
                <span>Solving OR-Tools VRP...</span>
              </>
            ) : (
              <>
                <Compass size={16} />
                <span>Generate route</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      <div className="plan-grid">
        {/* Card 1: Suggested Refill Amounts Table */}
        <section className="card plan-card">
          <div className="card-header-row">
            <div>
              <h2 className="section-title">Suggested refill amounts</h2>
              <p className="section-subtitle">
                Cash addition recommended based on forecasted demand and target safety capacity.
              </p>
            </div>
            <span className="badge badge-teal">{planItems.length} ATMs analyzed</span>
          </div>

          <div className="table-responsive plan-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ATM</th>
                  <th>Location</th>
                  <th>Cash Left</th>
                  <th>Add Cash</th>
                  <th>Risk Level</th>
                </tr>
              </thead>
              <tbody>
                {planItems.map((item) => (
                  <tr key={item.atm_id}>
                    <td className="font-semibold text-slate-800">{item.atm_id}</td>
                    <td>{item.location}</td>
                    <td>{formatLakhs(item.cash_left)}</td>
                    <td>
                      <span className="add-cash-val font-semibold text-teal-700">
                        {formatLakhs(item.add_cash)}
                      </span>
                    </td>
                    <td>
                      <span className={`risk-badge badge-${item.risk_level}`}>
                        {item.risk_level.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Card 2: Optimised Route (OR-Tools) */}
        <section className="card plan-card route-card">
          <div className="card-header-row">
            <div>
              <h2 className="section-title">Optimised route (OR-Tools)</h2>
              <p className="section-subtitle">
                Shortest distance TSP tour from Central Depot through high-risk ATMs and back.
              </p>
            </div>
          </div>

          {/* Route Metric Summary */}
          {routeData && (
            <div className="route-summary-bar">
              <div className="route-metric">
                <Truck size={18} className="metric-icon" />
                <div>
                  <span className="metric-label">Total Distance</span>
                  <strong className="metric-val">{routeData.total_distance_km} km</strong>
                </div>
              </div>

              <div className="route-metric">
                <Clock size={18} className="metric-icon" />
                <div>
                  <span className="metric-label">Estimated Time</span>
                  <strong className="metric-val">
                    {Math.floor(routeData.estimated_time_mins / 60)}h {routeData.estimated_time_mins % 60}m
                  </strong>
                </div>
              </div>

              <div className="route-metric">
                <MapPin size={18} className="metric-icon" />
                <div>
                  <span className="metric-label">ATMs on Route</span>
                  <strong className="metric-val">{routeData.atms_count} ATMs</strong>
                </div>
              </div>
            </div>
          )}

          {/* Numbered Step-by-Step Route List */}
          <div className="route-steps-container">
            {routeData?.steps ? (
              <ol className="numbered-route-list">
                {routeData.steps.map((step) => {
                  const isDepot = !step.atm_id;
                  return (
                    <li key={step.step} className={`route-step-item ${isDepot ? "step-depot" : ""}`}>
                      <div className="step-number-circle">{step.step}</div>
                      <div className="step-content">
                        <div className="step-title-line">
                          <strong className="step-title">{step.title}</strong>
                          {step.leg_distance_km > 0 && (
                            <span className="step-dist">+{step.leg_distance_km} km</span>
                          )}
                        </div>
                        <span className="step-loc">{step.location}</span>
                      </div>
                    </li>
                  );
                })}
              </ol>
            ) : (
              <p className="text-muted py-6 text-center">
                Click "Generate route" to calculate the replenishment path using Google OR-Tools.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
