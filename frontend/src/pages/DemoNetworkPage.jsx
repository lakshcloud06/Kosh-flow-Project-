import React, { useEffect, useState } from "react";
import { AlertTriangle, MapPin, TrendingUp } from "lucide-react";
import api from "../api/client";
import PlotlyChart from "../components/PlotlyChart";

export default function DemoNetworkPage() {
  const [atms, setAtms] = useState([]);
  const [selectedAtm, setSelectedAtm] = useState("");
  const [region, setRegion] = useState("All");
  const [forecast, setForecast] = useState(null);
  const [regionalForecast, setRegionalForecast] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/atms")
      .then((response) => {
        setAtms(response.data);
        if (response.data.length > 0) setSelectedAtm(response.data[0].atm_id);
      })
      .catch((requestError) => {
        console.error("Failed to load demo ATM locations:", requestError);
        setError("Unable to load the sample ATM network.");
      });
  }, []);

  useEffect(() => {
    if (!selectedAtm) return;
    api.get(`/forecast/atm/${selectedAtm}`, { params: { days: 7 } })
      .then((response) => setForecast(response.data))
      .catch((requestError) => {
        console.error("Failed to load demo ATM forecast:", requestError);
        setError("Unable to load the selected ATM forecast.");
      });
  }, [selectedAtm]);

  useEffect(() => {
    api.get("/forecast/region", { params: { region } })
      .then((response) => setRegionalForecast(response.data))
      .catch((requestError) => {
        console.error("Failed to load demo regional forecast:", requestError);
        setError("Unable to load the regional forecast.");
      });
  }, [region]);

  const regions = ["All", ...new Set(atms.map((atm) => atm.region))];
  const forecastChart = forecast ? [{
    x: forecast.forecasts.map((item) => item.day_name),
    y: forecast.forecasts.map((item) => item.predicted_demand / 100000),
    type: "bar",
    name: "Predicted demand",
    marker: { color: "#0F766E" },
  }] : [];

  return (
    <div className="demo-explorer-page">
      <div className="page-header">
        <div>
          <h1 className="welcome-text">ATM & Forecast Explorer</h1>
          <p className="welcome-subtext">Explore sample ATM locations, individual predictions, regional demand, and shortage risk.</p>
        </div>
      </div>

      <div className="demo-data-notice">Public demo · synthetic sample data only · no live ATM or account records</div>
      {error && <div className="error-banner"><AlertTriangle size={20} /><span>{error}</span></div>}

      <section className="card">
        <div className="chart-header">
          <div>
            <h2 className="section-title">ATM locations & shortage risk</h2>
            <p className="section-subtitle">Select a sample location to view its seven-day forecast.</p>
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

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr><th>ATM</th><th>City / Site</th><th>Region</th><th>Sample cash left</th><th>Demand / day</th><th>Shortage risk</th></tr>
            </thead>
            <tbody>
              {atms.map((atm) => (
                <tr key={atm.atm_id}>
                  <td className="font-semibold text-slate-800">{atm.atm_id}</td>
                  <td><MapPin size={14} className="demo-inline-icon" />{atm.city} · {atm.site_type}</td>
                  <td>{atm.region}</td>
                  <td>₹{(atm.cash_left / 100000).toFixed(2)} L</td>
                  <td>₹{(atm.expected_demand / 100000).toFixed(2)} L</td>
                  <td><span className={`risk-badge badge-${atm.risk_level}`}>{atm.risk_level.toUpperCase()}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="demo-explorer-grid">
        <section className="card">
          <div className="table-header">
            <div>
              <h2 className="section-title">Individual ATM prediction</h2>
              <p className="section-subtitle">{forecast ? `${forecast.atm_id} · ${forecast.city}` : "Loading sample forecast..."}</p>
            </div>
            <TrendingUp size={20} color="#0F766E" />
          </div>
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
          {forecast && (
            <div className="table-responsive">
              <table className="data-table">
                <thead><tr><th>Date</th><th>Demand</th><th>Projected cash</th><th>Risk</th></tr></thead>
                <tbody>
                  {forecast.forecasts.map((item) => (
                    <tr key={item.date}>
                      <td>{item.day_name} · {item.date}</td>
                      <td>₹{(item.predicted_demand / 100000).toFixed(2)} L</td>
                      <td>₹{(item.projected_cash_left / 100000).toFixed(2)} L</td>
                      <td><span className={`risk-badge badge-${item.risk_level}`}>{item.risk_level.toUpperCase()}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card">
          <div className="table-header">
            <div>
              <h2 className="section-title">Regional predictions</h2>
              <p className="section-subtitle">Aggregated sample outlook and shortage indicators.</p>
            </div>
            <label className="demo-select-label">
              Region
              <select value={region} onChange={(event) => setRegion(event.target.value)}>
                {regions.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
          </div>
          {regionalForecast && (
            <>
              <div className="demo-region-summary">
                <div><span>ATMs</span><strong>{regionalForecast.atm_count}</strong></div>
                <div><span>Avg. demand / day</span><strong>₹{(regionalForecast.average_daily_demand / 100000).toFixed(2)} L</strong></div>
                <div><span>High risk</span><strong>{regionalForecast.at_risk}</strong></div>
              </div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead><tr><th>Location</th><th>Demand / day</th><th>Risk</th></tr></thead>
                  <tbody>
                    {regionalForecast.locations.map((item) => (
                      <tr key={item.atm_id}>
                        <td>{item.city} · {item.atm_id}</td>
                        <td>₹{(item.predicted_demand / 100000).toFixed(2)} L</td>
                        <td><span className={`risk-badge badge-${item.risk_level}`}>{item.risk_level.toUpperCase()}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
