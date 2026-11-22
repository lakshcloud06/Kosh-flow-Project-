import React, { useState, useEffect } from "react";
import api from "../api/client";
import {
  Cpu,
  Target,
  ShieldAlert,
  CheckCircle,
  AlertCircle
} from "lucide-react";

export default function ModelPage() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const accuracy = metrics?.forecast_accuracy;
  const accuracyTargetMet = accuracy != null && accuracy >= 85;

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await api.get("/api/model/metrics");
        setMetrics(res.data);
      } catch (err) {
        console.error("Failed to load metrics:", err);
        setError("Unable to read model metrics from backend.");
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <div className="page-loader">
        <div className="spinner"></div>
        <p>Loading model evaluation telemetry...</p>
      </div>
    );
  }

  return (
    <div className="model-page">
      <div className="page-header">
        <div>
          <h1 className="welcome-text">Model Settings & Evaluation</h1>
          <p className="welcome-subtext">
            Performance parameters, forecasting accuracy metrics, and benchmark target compliance.
          </p>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Three Cards */}
      <div className="model-cards-grid">
        {/* Card 1: Model Accuracy */}
        <div className="card model-metric-card">
          <div className="metric-icon-box bg-blue-light">
            <Cpu size={24} color="#2563EB" />
          </div>
          <span className="metric-subtitle">Regression Fit (R² Score)</span>
          <h2 className="metric-large-num">{metrics?.model_accuracy == null ? "—" : `${metrics.model_accuracy}%`}</h2>
          <p className="metric-desc">
            Variance in daily cash withdrawals explained by calendar, location, UPI share, and weather features.
          </p>
          <div className="card-badge-row">
            <span className="badge badge-neutral">Test MAPE: {metrics?.test_mape ?? "—"}</span>
          </div>
        </div>

        {/* Card 2: Forecast Accuracy */}
        <div className="card model-metric-card highlight-card">
          <div className="metric-icon-box bg-teal-light">
            <Target size={24} color="#0F766E" />
          </div>
          <span className="metric-subtitle">Forecast Accuracy (100 - MAPE)</span>
          <h2 className="metric-large-num text-teal-700">{accuracy == null ? "—" : `${accuracy}%`}</h2>
          <p className="metric-desc">
            Evaluated on held-out test records across the 32 network ATMs, minimizing replenishment errors.
          </p>
          <div className="card-badge-row">
            <span className={`badge ${accuracyTargetMet ? "badge-success" : "badge-neutral"}`}>
              Target: &ge; 85% {accuracy == null ? "(Unavailable)" : accuracyTargetMet ? "(Achieved)" : "(Not met)"}
            </span>
          </div>
        </div>

        {/* Card 3: Cash-out Reduced */}
        <div className="card model-metric-card highlight-card">
          <div className="metric-icon-box bg-green-light">
            <ShieldAlert size={24} color="#16A34A" />
          </div>
          <span className="metric-subtitle">Cash-out Incidents Reduced</span>
          <h2 className="metric-large-num text-green-700">
            {metrics?.cash_out_reduced == null ? "Not measured" : `${metrics.cash_out_reduced}%`}
          </h2>
          <p className="metric-desc">
            No cash-out reduction metric is reported for the loaded model.
          </p>
          <div className="card-badge-row">
            <span className="badge badge-neutral">No verified reduction metric</span>
          </div>
        </div>
      </div>

      {/* Target Compliance Note & Technical Details Card */}
      <section className="card details-card">
        <div className="details-header">
          <CheckCircle size={22} color="#0F766E" />
          <h2 className="section-title">Validation Against System Performance Targets</h2>
        </div>

        <div className="details-content">
          <p>
            Koshflow's forecasting engine operates under two strict performance criteria designed
            to balance branch liquidity and cash transport logistics:
          </p>

          <div className="targets-comparison-grid">
            <div className="target-item">
              <div className="target-badge-label">Target 1: Forecast Accuracy &ge; 85%</div>
              <div className="target-status-line">
                <strong>Forecast accuracy: {accuracy == null ? "Unavailable" : `${accuracy}%`}</strong>
                {accuracy != null && (
                  <span className={`font-semibold ${accuracyTargetMet ? "text-teal-700" : "text-red-600"}`}>
                    {accuracyTargetMet
                      ? `(+${(accuracy - 85).toFixed(1)}% over target)`
                      : `(${(85 - accuracy).toFixed(1)}% below target)`}
                  </span>
                )}
              </div>
              <p className="target-explanation">
                Derived using Mean Absolute Percentage Error (MAPE) on test data:
                <code>Accuracy = 100 * (1 - MAPE)</code>.
                Lag momentum, day-of-week seasonality, and UPI digital transaction density
                prevent over-stocking and erratic cash estimates.
              </p>
            </div>

            <div className="target-item">
              <div className="target-badge-label">Cash-out reduction metric</div>
              <div className="target-status-line">
                <strong>Not reported by the loaded model evaluation</strong>
              </div>
              <p className="target-explanation">
                Koshflow does not display a simulated reduction as a measured model result.
              </p>
            </div>
          </div>

          <div className="engine-meta-footer">
            <div className="meta-col">
              <span className="meta-label">Model Architecture:</span>
              <span className="meta-val">{metrics?.model_name || "Unavailable"}</span>
            </div>
            <div className="meta-col">
              <span className="meta-label">Routing Engine:</span>
              <span className="meta-val">Google OR-Tools Vehicle Routing (TSP/VRP)</span>
            </div>
            <div className="meta-col">
              <span className="meta-label">Last Retrained:</span>
              <span className="meta-val">{metrics?.trained_at || "Unavailable"}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
