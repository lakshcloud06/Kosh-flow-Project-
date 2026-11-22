import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api/client";
import PlotlyChart from "../components/PlotlyChart";
import {
  AlertCircle,
  AlertTriangle,
  CalendarCheck,
  RefreshCw,
  TrendingUp,
} from "lucide-react";

const EMPTY_ANALYTICS = { data: [] };
const TREND_RANGES = [
  { value: "1", label: "1 Day" },
  { value: "7", label: "7 Days" },
  { value: "14", label: "14 Days" },
  { value: "30", label: "30 Days" },
];
const currencyInLakhs = (amount) =>
  amount == null ? "—" : `₹${(Number(amount) / 100000).toFixed(2)} L`;
const displayNumber = (value) =>
  value == null ? "—" : Number(value).toLocaleString("en-IN");
const shiftDate = (value, days) => {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [atms, setAtms] = useState([]);
  const [selectedAtm, setSelectedAtm] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [trendRange, setTrendRange] = useState("7");
  const [trend, setTrend] = useState(EMPTY_ANALYTICS);
  const [breakdown, setBreakdown] = useState(EMPTY_ANALYTICS);
  const [atmDemand, setAtmDemand] = useState(EMPTY_ANALYTICS);
  const [history, setHistory] = useState([]);
  const [forecast, setForecast] = useState({ items: [] });
  const [breakdownBy, setBreakdownBy] = useState("city");
  const [loading, setLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchSummary = async () => {
    setLoading(true);
    setError("");
    try {
      const [summaryResponse, atmsResponse] = await Promise.all([
        api.get("/api/dashboard/summary"),
        api.get("/api/atms"),
      ]);
      setSummary(summaryResponse.data);
      setAtms(atmsResponse.data);
    } catch (requestError) {
      console.error("Dashboard data request failed:", requestError);
      setError("Unable to load dataset-backed dashboard data from the Koshflow API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  useEffect(() => {
    let active = true;
    const fetchAnalytics = async () => {
      setAnalyticsLoading(true);
      setError("");
      const dateParams = {
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      };
      const periodEnd = endDate || summary?.date_end;
      const periodStart = periodEnd
        ? shiftDate(periodEnd, 1 - Number(trendRange))
        : "";
      const trendDateParams = periodEnd
        ? {
            start_date: startDate && startDate > periodStart ? startDate : periodStart,
            end_date: periodEnd,
          }
        : dateParams;
      try {
        const [trendResponse, breakdownResponse, atmResponse, historyResponse, forecastResponse] =
          await Promise.all([
            api.get("/api/analytics", {
              params: { ...trendDateParams, atm_id: selectedAtm || undefined, group_by: "date" },
            }),
            api.get("/api/analytics", {
              params: { ...dateParams, group_by: breakdownBy },
            }),
            api.get("/api/analytics", {
              params: { ...dateParams, group_by: "atm" },
            }),
            selectedAtm
              ? api.get(`/api/atms/${encodeURIComponent(selectedAtm)}/history`, { params: dateParams })
              : Promise.resolve({ data: { data: [] } }),
            selectedAtm
              ? api.get("/api/forecast", { params: { atm_id: selectedAtm, days: 7 } })
                .catch((requestError) => ({
                  data: {
                    items: [],
                    error: requestError.response?.data?.detail || "Model forecast is unavailable.",
                  },
                }))
              : Promise.resolve({ data: { items: [] } }),
          ]);
        if (!active) return;
        setTrend(trendResponse.data);
        setBreakdown(breakdownResponse.data);
        setAtmDemand(atmResponse.data);
        setHistory(historyResponse.data.data);
        setForecast(forecastResponse.data);
        if (forecastResponse.data.error) setError(forecastResponse.data.error);
      } catch (requestError) {
        if (!active) return;
        console.error("Dashboard analytics request failed:", requestError);
        setError(
          requestError.response?.data?.detail ||
            "Unable to load historical analytics or model forecasts."
        );
        setTrend(EMPTY_ANALYTICS);
        setBreakdown(EMPTY_ANALYTICS);
        setAtmDemand(EMPTY_ANALYTICS);
        setHistory([]);
        setForecast({ items: [] });
      } finally {
        if (active) setAnalyticsLoading(false);
      }
    };
    fetchAnalytics();
    return () => {
      active = false;
    };
  }, [startDate, endDate, selectedAtm, breakdownBy, trendRange, summary?.date_end]);

  const chartTraces = useMemo(() => {
    const traces = [{
      x: trend.data.map((item) => item.date),
      y: trend.data.map((item) =>
        item.actual_withdrawal == null ? null : item.actual_withdrawal / 100000
      ),
      type: "scatter",
      mode: "lines",
      name: "Actual withdrawal",
      line: { color: "#2563EB", width: 3 },
    }];
    if (trend.data.some((item) => item.predicted_demand != null)) {
      traces.push({
        x: trend.data.map((item) => item.date),
        y: trend.data.map((item) =>
          item.predicted_demand == null ? null : item.predicted_demand / 100000
        ),
        type: "scatter",
        mode: "lines",
        name: "Stored model prediction",
        line: { color: "#64748B", width: 2.5, dash: "dash" },
      });
    }
    return traces;
  }, [trend]);

  const cityTraces = [{
    x: breakdown.data.map((item) => item.city || item.region),
    y: breakdown.data.map((item) => item.actual_withdrawal / 100000),
    type: "bar",
    name: "Actual withdrawal",
    marker: { color: "#0F766E" },
  }];
  const atmTraces = [{
    x: atmDemand.data.map((item) => item.atm_id),
    y: atmDemand.data.map((item) => item.actual_withdrawal / 100000),
    type: "bar",
    name: "Actual withdrawal",
    marker: { color: "#2563EB" },
  }];
  const futureTraces = [{
    x: forecast.items.map((item) => item.date),
    y: forecast.items.map((item) => item.predicted_demand / 100000),
    type: "scatter",
    mode: "lines+markers",
    name: "Model forecast",
    line: { color: "#0F766E", width: 3 },
  }];

  const chartLayout = {
    autosize: true,
    margin: { l: 60, r: 25, t: 25, b: 65 },
    hovermode: "x unified",
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    yaxis: { title: "Withdrawal (₹ lakhs)", gridcolor: "#E2E8F0" },
    xaxis: { gridcolor: "#F1F5F9", type: "date", tickformat: "%b %d" },
    legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.22 },
  };

  if (loading) {
    return (
      <div className="page-loader">
        <div className="spinner"></div>
        <p>Loading ATM data from the connected dataset...</p>
      </div>
    );
  }

  const riskOrder = { high: 0, medium: 1 };
  const riskAtms = atms
    .filter((atm) => ["high", "medium"].includes(atm.risk_level))
    .sort((a, b) =>
      riskOrder[a.risk_level] - riskOrder[b.risk_level] ||
      (a.days_left ?? Number.POSITIVE_INFINITY) - (b.days_left ?? Number.POSITIVE_INFINITY)
    );
  const displayedRiskAtms = riskAtms.slice(0, 10);
  const selectedHistory = history.slice(-30).reverse();

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <div>
          <h1 className="welcome-text">Welcome back, {user?.full_name || "Operations Lead"}</h1>
          <p className="welcome-subtext">
            Actual ATM demand, historical model validation, and dataset-based replenishment risk.
          </p>
        </div>
        <button
          className="btn btn-secondary btn-sm refresh-btn"
          onClick={fetchSummary}
          title="Refresh dataset metrics"
        >
          <RefreshCw size={15} />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      <section className="kpi-grid dataset-kpi-grid">
        <MetricCard icon={<TrendingUp size={22} />} tone="blue" label="Total ATMs" value={displayNumber(summary?.total_atms)} />
        <MetricCard icon={<CalendarCheck size={22} />} tone="teal" label="Historical records" value={displayNumber(summary?.total_records)} />
        <MetricCard icon={<TrendingUp size={22} />} tone="green" label="Average withdrawal / ATM-day" value={currencyInLakhs(summary?.average_daily_withdrawal)} />
        <MetricCard icon={<AlertTriangle size={22} />} tone="red" label="ATMs at shortage risk" value={displayNumber(summary?.atms_at_risk)} />
        <MetricCard icon={<RefreshCw size={22} />} tone="blue" label="Refills planned this week" value={displayNumber(summary?.refill_recommendations ?? 0)} />
      </section>

      <section className="card">
        <div className="chart-header">
          <div>
            <h2 className="section-title">Dataset filters</h2>
            <p className="section-subtitle">
              Historical coverage: {summary?.date_start || "—"} to {summary?.date_end || "—"}
            </p>
          </div>
          <div className="dataset-filters">
            <label>
              ATM
              <select value={selectedAtm} onChange={(event) => setSelectedAtm(event.target.value)}>
                <option value="">All ATMs</option>
                {atms.map((atm) => (
                  <option key={atm.atm_id} value={atm.atm_id}>{atm.atm_id} · {atm.city}</option>
                ))}
              </select>
            </label>
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
      </section>

      <section className="card chart-card">
        <div className="chart-header">
          <div>
            <h2 className="section-title">Historical withdrawals: actual vs stored prediction</h2>
            <p className="section-subtitle">
              Actual values cover the selected historical period. Stored model predictions appear only for dates with prediction records.
            </p>
          </div>
          <div className="range-button-group" role="group" aria-label="Historical time period">
            {TREND_RANGES.map((range) => (
              <button
                key={range.value}
                type="button"
                className={`range-btn ${trendRange === range.value ? "range-btn-active" : ""}`}
                aria-pressed={trendRange === range.value}
                onClick={() => setTrendRange(range.value)}
              >
                {range.label}
              </button>
            ))}
          </div>
        </div>
        <div className="chart-container">
          {analyticsLoading ? (
            <div className="chart-spinner-overlay"><div className="spinner"></div></div>
          ) : trend.data.length ? (
            <PlotlyChart data={chartTraces} layout={chartLayout} config={{ displayModeBar: false, responsive: true }} />
          ) : (
            <p className="text-center py-4 text-muted">No historical demand exists for the selected filters.</p>
          )}
        </div>
      </section>

      <div className="demo-explorer-grid">
        <section className="card chart-card">
          <div className="chart-header">
            <div>
              <h2 className="section-title">City and regional demand</h2>
              <p className="section-subtitle">
                Region labels are derived from the dataset’s city field; demand values are aggregated from database records.
              </p>
            </div>
            <label className="demo-select-label">
              Group by
              <select value={breakdownBy} onChange={(event) => setBreakdownBy(event.target.value)}>
                <option value="city">City</option>
                <option value="region">Region</option>
              </select>
            </label>
          </div>
          <div className="chart-container">
            {breakdown.data.length ? (
              <PlotlyChart data={cityTraces} layout={chartLayout} config={{ displayModeBar: false, responsive: true }} />
            ) : <p className="text-center py-4 text-muted">No city or region data for this date range.</p>}
          </div>
        </section>

        <section className="card chart-card">
          <div className="chart-header">
            <div>
              <h2 className="section-title">ATM-wise cash demand</h2>
              <p className="section-subtitle">Total actual withdrawals for the selected date range.</p>
            </div>
          </div>
          <div className="chart-container">
            {atmDemand.data.length ? (
              <PlotlyChart data={atmTraces} layout={{ ...chartLayout, xaxis: { ...chartLayout.xaxis, tickangle: -45 } }} config={{ displayModeBar: false, responsive: true }} />
            ) : <p className="text-center py-4 text-muted">No ATM demand data for this date range.</p>}
          </div>
        </section>
      </div>

      {selectedAtm && (
        <div className="demo-explorer-grid">
          <section className="card chart-card">
            <div className="chart-header">
              <div>
                <h2 className="section-title">Existing model forecast</h2>
                <p className="section-subtitle">
                  Forecast origin: {forecast.forecast_origin_date || "—"} · {forecast.assumptions || ""}
                </p>
              </div>
            </div>
            <div className="chart-container">
              {forecast.items.length ? (
                <PlotlyChart data={futureTraces} layout={chartLayout} config={{ displayModeBar: false, responsive: true }} />
              ) : <p className="text-center py-4 text-muted">No model forecast is available.</p>}
            </div>
          </section>

          <section className="card table-card">
            <div className="table-header">
              <div>
                <h2 className="section-title">{selectedAtm} historical records</h2>
                <p className="section-subtitle">Latest 30 records in the selected date range.</p>
              </div>
              <span className="badge badge-neutral">{history.length} records</span>
            </div>
            <div className="table-responsive">
              <table className="data-table">
                <thead><tr><th>Date</th><th>Withdrawal</th><th>Replenished</th><th>Closing balance</th><th>Stored prediction</th></tr></thead>
                <tbody>
                  {selectedHistory.length ? selectedHistory.map((item) => (
                    <tr key={item.date}>
                      <td>{item.date}</td>
                      <td>{currencyInLakhs(item.withdrawal_amount)}</td>
                      <td>{currencyInLakhs(item.cash_replenished)}</td>
                      <td>{currencyInLakhs(item.balance_closing)}</td>
                      <td>{currencyInLakhs(item.predicted_demand)}</td>
                    </tr>
                  )) : (
                    <tr><td colSpan="5" className="text-center py-4 text-muted">No history for the selected ATM and date range.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      <section className="card table-card">
        <div className="table-header">
          <div>
            <h2 className="section-title">ATMs needing replenishment</h2>
            <p className="section-subtitle">Risk is calculated from each ATM’s latest recorded cash balance and stored forecast.</p>
          </div>
          <div className="table-header-actions">
            <span className="badge badge-neutral">{riskAtms.length} ATMs at elevated risk</span>
            <Link to="/plan" className="btn btn-secondary btn-sm">View All</Link>
          </div>
        </div>
        <div className="table-responsive">
          <table className="data-table">
            <thead><tr><th>ATM</th><th>City</th><th>Cash as of</th><th>Cash left</th><th>Expected daily demand</th><th>Risk</th></tr></thead>
            <tbody>
              {displayedRiskAtms.length ? displayedRiskAtms.map((atm) => (
                <tr key={atm.atm_id}>
                  <td className="font-semibold text-slate-800">{atm.atm_id}</td>
                  <td>{atm.city} · {atm.region}</td>
                  <td>{atm.cash_as_of}</td>
                  <td>{currencyInLakhs(atm.cash_left)}</td>
                  <td>{currencyInLakhs(atm.average_daily_demand)}</td>
                  <td><span className={`risk-badge badge-${atm.risk_level}`}>{atm.risk_level.toUpperCase()}</span></td>
                </tr>
              )) : (
                <tr><td colSpan="6" className="text-center py-4 text-muted">
                  {atms.length ? "No ATM has an elevated shortage risk in the available forecast data." : "No ATM records are available."}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function MetricCard({ icon, tone, label, value }) {
  return (
    <div className="card kpi-card">
      <div className={`kpi-icon-wrapper kpi-${tone}`}>{icon}</div>
      <div className="kpi-content">
        <span className="kpi-label">{label}</span>
        <h2 className="kpi-value">{value}</h2>
      </div>
    </div>
  );
}
