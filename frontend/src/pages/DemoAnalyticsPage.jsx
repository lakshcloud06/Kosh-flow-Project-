import React, { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";
import api from "../api/client";
import PlotlyChart from "../components/PlotlyChart";

export default function DemoAnalyticsPage() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [series, setSeries] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api.get("/api/analytics", {
      params: {
        group_by: "date",
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      },
    })
      .then((response) => {
        if (!active) return;
        setSeries(response.data.data);
        setError("");
      })
      .catch((requestError) => {
        if (!active) return;
        console.error("Failed to load historical analytics:", requestError);
        setError(requestError.response?.data?.detail || "Unable to load historical analytics from the dataset.");
        setSeries([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [startDate, endDate]);

  const downloadReport = () => {
    if (!series.length) return;
    const rows = [["Date", "Actual demand (rupees)", "Stored model prediction (rupees)"]];
    series.forEach((item) => rows.push([
      item.date,
      item.actual_withdrawal,
      item.predicted_demand ?? "",
    ]));
    const csv = rows.map((row) =>
      row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")
    ).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "koshflow-dataset-analytics.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const chartData = [
    {
      x: series.map((item) => item.date),
      y: series.map((item) => item.actual_withdrawal / 100000),
      type: "scatter",
      mode: "lines",
      name: "Actual withdrawal",
      line: { color: "#2563EB", width: 3 },
    },
    {
      x: series.map((item) => item.date),
      y: series.map((item) =>
        item.predicted_demand == null ? null : item.predicted_demand / 100000
      ),
      type: "scatter",
      mode: "lines",
      name: "Stored model prediction",
      line: { color: "#0F766E", width: 3, dash: "dash" },
    },
  ];

  return (
    <div className="demo-analytics-page">
      <div className="page-header">
        <div>
          <h1 className="welcome-text">Historical Analytics & Reports</h1>
          <p className="welcome-subtext">Explore actual withdrawals and stored model predictions from the connected dataset.</p>
        </div>
        <button type="button" className="btn btn-teal" onClick={downloadReport} disabled={!series.length}>
          <Download size={16} />
          <span>Download CSV report</span>
        </button>
      </div>

      {error && <div className="error-banner" role="alert"><FileText size={20} /><span>{error}</span></div>}

      <section className="card chart-card">
        <div className="chart-header">
          <div>
            <h2 className="section-title">Historical demand: actual vs stored prediction</h2>
            <p className="section-subtitle">Predictions are present only for dates in the model’s stored validation output.</p>
          </div>
          <div className="dataset-filters">
            <label>
              From
              <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
            </label>
            <label>
              To
              <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
            </label>
          </div>
        </div>
        <div className="chart-container">
          {loading ? (
            <div className="chart-spinner-overlay"><div className="spinner"></div></div>
          ) : series.length ? (
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
          ) : <p className="text-center py-4 text-muted">No historical data exists for the selected date range.</p>}
        </div>
      </section>

      {series.length > 0 && (
        <section className="card">
          <div className="table-header">
            <div>
              <h2 className="section-title">Historical data</h2>
              <p className="section-subtitle">{series.length.toLocaleString("en-IN")} dates from the selected period.</p>
            </div>
          </div>
          <div className="table-responsive">
            <table className="data-table">
              <thead><tr><th>Date</th><th>Actual withdrawal (₹)</th><th>Stored prediction (₹)</th><th>Variance (₹)</th></tr></thead>
              <tbody>
                {series.slice(-90).reverse().map((item) => (
                  <tr key={item.date}>
                    <td>{item.date}</td>
                    <td>{Number(item.actual_withdrawal).toLocaleString("en-IN")}</td>
                    <td>{item.predicted_demand == null ? "—" : Number(item.predicted_demand).toLocaleString("en-IN")}</td>
                    <td>{item.predicted_demand == null
                      ? "—"
                      : Number(item.actual_withdrawal - item.predicted_demand).toLocaleString("en-IN")}
                    </td>
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
