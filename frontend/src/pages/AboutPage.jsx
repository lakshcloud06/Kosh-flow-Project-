import React from "react";
import {
  ShieldCheck,
  Cpu,
  Truck,
  Database,
  ArrowRight,
  TrendingDown,
  Target
} from "lucide-react";

export default function AboutPage() {
  const steps = [
    {
      num: "01",
      icon: Database,
      title: "Data Ingestion & Cleaning",
      desc: "Aggregates raw daily ATM transactions, opening balances, deposit flows, downtime logs, and external signals (local footfall, weather, UPI penetration). Imputes missing records and strips anomalies."
    },
    {
      num: "02",
      icon: Cpu,
      title: "Machine Learning Forecasting",
      desc: "Engineers lag momentum, rolling averages, calendar events, and salary periods. Trains a Gradient Boosting regression model achieving >90% forecast accuracy on ATM withdrawal demands."
    },
    {
      num: "03",
      icon: Truck,
      title: "Route & Replenishment Optimization",
      desc: "Computes run-out horizon for each ATM. Evaluates risk levels (High, Medium, Normal) and executes Google OR-Tools routing to create shortest-distance multi-stop armored van tours from Central Depot."
    }
  ];

  return (
    <div className="about-page">
      <div className="page-header">
        <div>
          <h1 className="welcome-text">About Koshflow</h1>
          <p className="welcome-subtext">
            ATM cash demand forecasting and smart replenishment logistics.
          </p>
        </div>
      </div>

      <div className="card about-main-card">
        <div className="about-hero">
          <div className="about-badge-icon">
            <ShieldCheck size={38} color="#0F766E" />
          </div>
          <div>
            <h2 className="about-title">Intelligent Liquidity Management for Modern Banking</h2>
            <p className="about-lead">
              Koshflow bridges ATM cash inventory telemetry and route logistics. By predicting
              exact daily cash withdrawals before they happen, financial institutions eliminate
              costly cash-out incidents, reduce unneeded idle cash in machines, and lower armored
              carrier transportation expenses.
            </p>
          </div>
        </div>

        {/* How it works pipeline */}
        <div className="pipeline-section">
          <h3 className="pipeline-title">How Koshflow Works</h3>
          <div className="steps-grid">
            {steps.map((step) => {
              const Icon = step.icon;
              return (
                <div key={step.num} className="step-card">
                  <div className="step-header">
                    <span className="step-idx">{step.num}</span>
                    <div className="step-icon-wrap">
                      <Icon size={20} color="#0F766E" />
                    </div>
                  </div>
                  <h4 className="step-card-title">{step.title}</h4>
                  <p className="step-card-desc">{step.desc}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Strategic Goals Section */}
        <div className="goals-section">
          <h3 className="pipeline-title">Operational Targets & Impact</h3>
          <div className="goals-grid">
            <div className="goal-card">
              <Target size={24} color="#0F766E" />
              <h4>Forecast Accuracy &ge; 85%</h4>
              <p>
                Eliminates guess-work by accurately forecasting daily withdrawal volumes within a narrow margin of error across branches and remote standalone ATMs.
              </p>
            </div>

            <div className="goal-card">
              <TrendingDown size={24} color="#DC2626" />
              <h4>Cash-Outs Reduced &ge; 70%</h4>
              <p>
                Prevents ATM service interruptions by alerting logistics dispatchers before balances fall below the 24-hour critical run-out boundary.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
