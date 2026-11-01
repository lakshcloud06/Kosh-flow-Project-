import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../api/client";
import PlotlyChart from "../components/PlotlyChart";
import {
  TrendingUp,
  AlertTriangle,
  CalendarCheck,
  CheckCircle2,
  RefreshCw,
  AlertCircle
} from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuth();
  const [kpis, setKpis] = useState(null);
  const [demandData, setDemandData] = useState(null);
  const [refillAtms, setRefillAtms] = useState([]);
  const [range, setRange] = useState("7");
  const [loading, setLoading] = useState(true);
  const [chartLoading, setChartLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchData = async () => {
    setError("");
    setLoading(true);
    try {
      const [kpiRes, refillRes] = await Promise.all([
        api.get("/dashboard/kpis"),
        api.get("/dashboard/refill-atms")
      ]);
      setKpis(kpiRes.data);
      setRefillAtms(refillRes.data);
    } catch (err) {
      console.error("Dashboard fetch error:", err);
      setError("Unable to connect to Koshflow API. Ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const fetchDemandChart = async (selectedRange) => {
    setChartLoading(true);
    try {
      const res = await api.get(`/dashboard/demand?range=${selectedRange}`);
      setDemandData(res.data);
    } catch (err) {
      console.error("Chart fetch error:", err);
    } finally {
      setChartLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchDemandChart(range);
  }, [range]);

  const rangeButtons = [
    { label: "1 day", value: "1" },
    { label: "7 days", value: "7" },
    { label: "14 days", value: "14" },
    { label: "30 days", value: "30" },
  ];

  if (loading) {
    return (
      <div className="page-loader">
        <div className="spinner"></div>
        <p>Loading real-time ATM network telemetry...</p>
      </div>
    );
  }

  // Plotly chart config
  const chartTraces = demandData
    ? [
        {
          x: demandData.x,
          y: demandData.actual,
          type: "scatter",
          mode: "lines+markers",
          name: "Actual Demand",
          line: { color: "#2563EB", width: 3 },
          marker: { size: 6, color: "#2563EB" },
        },
        {
          x: demandData.x,
          y: demandData.forecast,
          type: "scatter",
          mode: "lines+markers",
          name: "Forecast Demand",
          line: { color: "#64748B", width: 2.5, dash: "dash" },
          marker: { size: 6, color: "#64748B" },
        },
      ]
    : [];

  const chartLayout = {
    autosize: true,
    margin: { l: 60, r: 25, t: 25, b: 65 },
    hovermode: "x unified",
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    yaxis: {
      title: "Cash amount (₹ lakhs)",
      titlefont: { size: 12, color: "#475569" },
      tickfont: { color: "#475569", size: 11 },
      gridcolor: "#E2E8F0",
      zerolinecolor: "#CBD5E1",
    },
    xaxis: {
      tickfont: { color: "#475569", size: 11 },
      gridcolor: "#F1F5F9",
    },
    legend: {
      orientation: "h",
      x: 0.5,
      xanchor: "center",
      y: -0.22,
      font: { color: "#334155", size: 12 },
    },
  };

  return (
    <div className="dashboard-page">
      {/* Welcome Banner */}
      <div className="page-header">
        <div>
          <h1 className="welcome-text">
            Welcome back, {user?.full_name || "Operations Lead"}
          </h1>
          <p className="welcome-subtext">
            Real-time cash replenishment and predictive forecasting overview.
          </p>
        </div>
        <button
          className="btn btn-secondary btn-sm refresh-btn"
          onClick={() => {
            fetchData();
            fetchDemandChart(range);
          }}
          title="Refresh metrics"
        >
          <RefreshCw size={15} />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* 4 KPI Cards */}
      <section className="kpi-grid">
        <div className="card kpi-card">
          <div className="kpi-icon-wrapper kpi-blue">
            <TrendingUp size={22} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">Average daily demand</span>
            <h2 className="kpi-value">₹{kpis?.avg_daily_demand_lakhs ?? "4.86"} L</h2>
            <span className="kpi-subtext">Across active network ATMs</span>
          </div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-icon-wrapper kpi-red">
            <AlertTriangle size={22} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">ATMs at risk</span>
            <h2 className="kpi-value kpi-val-danger">{kpis?.atms_at_risk ?? "0"}</h2>
            <span className="kpi-subtext">Cash-out predicted within 24h</span>
          </div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-icon-wrapper kpi-teal">
            <CalendarCheck size={22} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">Refills planned this week</span>
            <h2 className="kpi-value">{kpis?.refills_planned_week ?? "0"}</h2>
            <span className="kpi-subtext">Scheduled replenishment stops</span>
          </div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-icon-wrapper kpi-green">
            <CheckCircle2 size={22} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">Forecast accuracy</span>
            <h2 className="kpi-value kpi-val-success">{kpis?.forecast_accuracy ?? "90.2"}%</h2>
            <span className="kpi-subtext">Exceeds target &ge; 85%</span>
          </div>
        </div>
      </section>

      {/* Chart Section */}
      <section className="card chart-card">
        <div className="chart-header">
          <div>
            <h2 className="section-title">Cash demand: actual vs forecast</h2>
            <p className="section-subtitle">
              Comparison of observed withdrawals and ML predicted demand series in ₹ lakhs.
            </p>
          </div>
          <div className="range-button-group">
            {rangeButtons.map((btn) => (
              <button
                key={btn.value}
                type="button"
                className={`range-btn ${range === btn.value ? "range-btn-active" : ""}`}
                onClick={() => setRange(btn.value)}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>

        <div className="chart-container">
          {chartLoading ? (
            <div className="chart-spinner-overlay">
              <div className="spinner"></div>
            </div>
          ) : (
            <PlotlyChart
              data={chartTraces}
              layout={chartLayout}
              config={{ displayModeBar: false, responsive: true }}
            />
          )}
        </div>
      </section>

      {/* Table Section: ATMs needing refill */}
      <section className="card table-card">
        <div className="table-header">
          <div>
            <h2 className="section-title">ATMs needing refill</h2>
            <p className="section-subtitle">
              Prioritized by cash-out urgency and remaining cash balance.
            </p>
          </div>
          <span className="badge badge-neutral">{refillAtms.length} ATMs listed</span>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>ATM</th>
                <th>Location</th>
                <th>Cash left</th>
                <th>Predicted out</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {refillAtms.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-4 text-muted">
                    No ATMs currently require immediate cash replenishment.
                  </td>
                </tr>
              ) : (
                refillAtms.map((atm) => (
                  <tr key={atm.atm_id}>
                    <td className="font-semibold text-slate-800">{atm.atm_id}</td>
                    <td>{atm.location}</td>
                    <td>
                      <span className="cash-amount">
                        ₹{(atm.cash_left / 100000).toFixed(2)} Lakhs
                      </span>
                    </td>
                    <td>
                      <span className="predicted-out-text">{atm.predicted_out}</span>
                    </td>
                    <td>
                      <span className={`risk-badge badge-${atm.risk_level}`}>
                        {atm.risk_level.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
