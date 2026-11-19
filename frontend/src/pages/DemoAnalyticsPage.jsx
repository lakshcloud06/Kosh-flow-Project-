import React, { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";
import api from "../api/client";
import PlotlyChart from "../components/PlotlyChart";

export default function DemoAnalyticsPage() {
  const [range, setRange] = useState("30");
  const [series, setSeries] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/analytics", { params: { range } })
      .then((response) => {
        setSeries(response.data);
        setError("");
      })
      .catch((requestError) => {
        console.error("Failed to load demo historical analytics:", requestError);
        setError("Unable to load sample historical analytics.");
      });
  }, [range]);

  const downloadReport = () => {
    if (!series) return;
    const rows = [["Date", "Actual demand (lakhs)", "Forecast demand (lakhs)"]];
    series.x.forEach((day, index) => rows.push([day, series.actual[index], series.forecast[index]]));
    const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `koshflow-demo-report-${range}-days.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const chartData = series ? [
    { x: series.x, y: series.actual, type: "scatter", mode: "lines+markers", name: "Sample actual", line: { color: "#2563EB", width: 3 } },
    { x: series.x, y: series.forecast, type: "scatter", mode: "lines+markers", name: "Sample forecast", line: { color: "#0F766E", width: 3, dash: "dash" } },
  ] : [];

  return (
    <div className="demo-analytics-page">
      <div className="page-header">
        <div>
          <h1 className="welcome-text">Historical Analytics & Reports</h1>
          <p className="welcome-subtext">Compare sample ATM cash demand and forecasts across a selected period.</p>
        </div>
        <button type="button" className="btn btn-teal" onClick={downloadReport} disabled={!series}>
          <Download size={16} />
          <span>Download CSV report</span>
        </button>
      </div>

      <div className="demo-data-notice">Public demo · synthetic sample data only · exported report contains no live records</div>
      {error && <div className="error-banner"><FileText size={20} /><span>{error}</span></div>}

      <section className="card chart-card">
        <div className="chart-header">
          <div>
            <h2 className="section-title">Historical demand: actual vs forecast</h2>
            <p className="section-subtitle">Illustrative network averages in ₹ lakhs per ATM per day.</p>
          </div>
          <label className="demo-select-label">
            Period
            <select value={range} onChange={(event) => setRange(event.target.value)}>
              <option value="7">7 days</option>
              <option value="30">30 days</option>
              <option value="90">90 days</option>
            </select>
          </label>
        </div>
        <div className="chart-container">
          <PlotlyChart
            data={chartData}
            layout={{
              autosize: true,
              margin: { l: 60, r: 20, t: 20, b: 65 },
              hovermode: "x unified",
              paper_bgcolor: "transparent",
              plot_bgcolor: "transparent",
              yaxis: { title: "₹ lakhs", gridcolor: "#E2E8F0" },
              xaxis: { gridcolor: "#F1F5F9" },
              legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.22 },
            }}
            config={{ displayModeBar: false, responsive: true }}
          />
        </div>
      </section>

      {series && (
        <section className="card">
          <div className="table-header">
            <div>
              <h2 className="section-title">Historical data</h2>
              <p className="section-subtitle">{series.x.length} sample periods · downloadable as CSV.</p>
            </div>
            <span className="badge badge-neutral">Demo report</span>
          </div>
          <div className="table-responsive">
            <table className="data-table">
              <thead><tr><th>Date</th><th>Sample actual (₹ L)</th><th>Sample forecast (₹ L)</th><th>Variance (₹ L)</th></tr></thead>
              <tbody>
                {series.x.map((day, index) => (
                  <tr key={`${day}-${index}`}>
                    <td>{day}</td>
                    <td>{series.actual[index].toFixed(2)}</td>
                    <td>{series.forecast[index].toFixed(2)}</td>
                    <td>{(series.actual[index] - series.forecast[index]).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
