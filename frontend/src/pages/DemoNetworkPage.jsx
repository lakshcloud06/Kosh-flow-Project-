import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, MapPin, TrendingUp } from "lucide-react";
import api from "../api/client";
import PlotlyChart from "../components/PlotlyChart";

const moneyInLakhs = (value) =>
  value == null ? "—" : `₹${(Number(value) / 100000).toFixed(2)} L`;

export default function DemoNetworkPage() {
  const [atms, setAtms] = useState([]);
  const [selectedAtm, setSelectedAtm] = useState("");
  const [region, setRegion] = useState("All");
  const [forecast, setForecast] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/api/atms")
      .then((response) => {
        setAtms(response.data);
        if (response.data.length > 0) setSelectedAtm(response.data[0].atm_id);
      })
      .catch((requestError) => {
        console.error("Failed to load ATM data:", requestError);
        setError("Unable to load ATM data from the connected dataset.");
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedAtm) {
      setForecast(null);
      return;
    }
    api.get("/api/forecast", { params: { atm_id: selectedAtm, days: 7 } })
      .then((response) => {
        setForecast(response.data);
        setError("");
      })
      .catch((requestError) => {
        console.error("Failed to load model forecast:", requestError);
        setForecast(null);
        setError(requestError.response?.data?.detail || "Unable to load the model forecast.");
      });
  }, [selectedAtm]);

  const regions = useMemo(
    () => ["All", ...new Set(atms.map((atm) => atm.region).filter(Boolean))],
    [atms]
  );
  const regionalAtms = atms.filter((atm) => region === "All" || atm.region === region);
  const regionalDemand = regionalAtms.filter((atm) => atm.average_daily_demand != null);
  const averageRegionalDemand = regionalDemand.length
    ? regionalDemand.reduce((sum, atm) => sum + atm.average_daily_demand, 0) / regionalDemand.length
    : null;
  const regionalForecast = {
    atm_count: regionalAtms.length,
    average_daily_demand: averageRegionalDemand,
    at_risk: regionalAtms.filter((atm) => atm.risk_level === "high").length,
  };
  const forecastItems = forecast?.items || [];
  const forecastChart = forecastItems.length ? [{
    x: forecastItems.map((item) => item.date),
    y: forecastItems.map((item) => item.predicted_demand / 100000),
    type: "bar",
    name: "Model prediction",
    marker: { color: "#0F766E" },
  }] : [];

  return (
    <div className="demo-explorer-page">
      <div className="page-header">
        <div>
          <h1 className="welcome-text">ATM & Forecast Explorer</h1>
          <p className="welcome-subtext">Explore recorded ATM demand, model forecasts, and shortage risk.</p>
        </div>
      </div>

      {error && <div className="error-banner" role="alert"><AlertTriangle size={20} /><span>{error}</span></div>}

      <section className="card">
        <div className="chart-header">
          <div>
            <h2 className="section-title">ATM network & shortage risk</h2>
            <p className="section-subtitle">Balances and demand are from the latest available dataset records.</p>
          </div>
          <label className="demo-select-label">
            ATM location
            <select value={selectedAtm} onChange={(event) => setSelectedAtm(event.target.value)}>
              {atms.map((atm) => (
                <option key={atm.atm_id} value={atm.atm_id}>{atm.atm_id} · {atm.city}</option>
              ))}
            </select>
          </label>
        </div>

        {loading ? <p className="text-center py-4 text-muted">Loading ATM records...</p> : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr><th>ATM</th><th>City / Site</th><th>Region</th><th>Cash as of</th><th>Cash left</th><th>Avg demand / day</th><th>Risk</th></tr>
              </thead>
              <tbody>
                {atms.length ? atms.map((atm) => (
                  <tr key={atm.atm_id}>
                    <td className="font-semibold text-slate-800">{atm.atm_id}</td>
                    <td><MapPin size={14} className="demo-inline-icon" />{atm.city} · {atm.site_type}</td>
                    <td>{atm.region}</td>
                    <td>{atm.cash_as_of || "—"}</td>
                    <td>{moneyInLakhs(atm.cash_left)}</td>
                    <td>{moneyInLakhs(atm.average_daily_demand)}</td>
                    <td><span className={`risk-badge badge-${atm.risk_level}`}>{atm.risk_level.toUpperCase()}</span></td>
                  </tr>
                )) : (
                  <tr><td colSpan="7" className="text-center py-4 text-muted">No ATM records are available.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="demo-explorer-grid">
        <section className="card">
          <div className="table-header">
            <div>
              <h2 className="section-title">Individual ATM prediction</h2>
              <p className="section-subtitle">
                {forecast
                  ? `${selectedAtm} · forecast after ${forecast.forecast_origin_date}`
                  : "Select an ATM to load model predictions."}
              </p>
            </div>
            <TrendingUp size={20} color="#0F766E" />
          </div>
          {forecastItems.length ? (
            <>
              <div className="chart-container">
                <PlotlyChart
                  data={forecastChart}
                  layout={{
                    autosize: true,
                    margin: { l: 55, r: 15, t: 15, b: 45 },
                    paper_bgcolor: "transparent",
                    plot_bgcolor: "transparent",
                    yaxis: { title: "₹ lakhs", gridcolor: "#E2E8F0" },
                    xaxis: { gridcolor: "#F1F5F9" },
                    showlegend: false,
                  }}
                  config={{ displayModeBar: false, responsive: true }}
                />
              </div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead><tr><th>Date</th><th>Predicted demand</th><th>Projected cash</th><th>Risk</th></tr></thead>
                  <tbody>
                    {forecastItems.map((item) => (
                      <tr key={item.date}>
                        <td>{item.day_name} · {item.date}</td>
                        <td>{moneyInLakhs(item.predicted_demand)}</td>
                        <td>{moneyInLakhs(item.projected_cash_left)}</td>
                        <td><span className={`risk-badge badge-${item.risk_level}`}>{item.risk_level.toUpperCase()}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : <p className="text-center py-4 text-muted">No forecast is available for this ATM.</p>}
        </section>

        <section className="card">
          <div className="table-header">
            <div>
              <h2 className="section-title">Regional demand</h2>
              <p className="section-subtitle">Regional labels are derived from the dataset’s city values.</p>
            </div>
            <label className="demo-select-label">
              Region
              <select value={region} onChange={(event) => setRegion(event.target.value)}>
                {regions.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
          </div>
          <div className="demo-region-summary">
            <div><span>ATMs</span><strong>{regionalForecast.atm_count}</strong></div>
            <div><span>Avg. forecast demand / day</span><strong>{moneyInLakhs(regionalForecast.average_daily_demand)}</strong></div>
            <div><span>High risk</span><strong>{regionalForecast.at_risk}</strong></div>
          </div>
          <div className="table-responsive">
            <table className="data-table">
              <thead><tr><th>Location</th><th>Avg demand / day</th><th>Risk</th></tr></thead>
              <tbody>
                {regionalAtms.length ? regionalAtms.map((atm) => (
                  <tr key={atm.atm_id}>
                    <td>{atm.city} · {atm.atm_id}</td>
                    <td>{moneyInLakhs(atm.average_daily_demand)}</td>
                    <td><span className={`risk-badge badge-${atm.risk_level}`}>{atm.risk_level.toUpperCase()}</span></td>
                  </tr>
                )) : (
                  <tr><td colSpan="3" className="text-center py-4 text-muted">No ATMs match this region.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
