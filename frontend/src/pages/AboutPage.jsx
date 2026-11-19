import React from "react";
import {
  Cpu,
  Truck,
  Database,
  TrendingDown,
  Target,
  GraduationCap,
  BookOpen,
  ExternalLink,
  UserCheck
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
        {/* Developer Profile Section */}
        <div className="developer-profile-hero">
          <div className="developer-section-tag">
            <UserCheck size={16} />
            <span>About the Developer</span>
          </div>

          <div className="developer-hero-body">
            <div className="developer-avatar-wrapper">
              <div className="developer-avatar">
                <span>LA</span>
              </div>
            </div>

            <div className="developer-details">
              <h2 className="developer-name">Lakshay Aggarwal</h2>

              <div className="developer-meta-list">
                <div className="developer-meta-item">
                  <GraduationCap size={16} className="developer-meta-icon" />
                  <span className="developer-meta-text">
                    <strong>College:</strong> ABES Engineering College, Ghaziabad, Uttar Pradesh
                  </span>
                </div>
                <div className="developer-meta-item">
                  <BookOpen size={16} className="developer-meta-icon" />
                  <span className="developer-meta-text">
                    <strong>Course:</strong> B.Tech – Electrical and Computer Engineering (ELCE)
                  </span>
                </div>
              </div>

              <p className="developer-bio">
                I am Lakshay Aggarwal, a third-year B.Tech student at ABES Engineering College, Ghaziabad. I developed Koshflow as an AI-powered ATM Cash Demand Prediction and Liquidity Management project, focused on forecasting ATM cash requirements, reducing cash-out incidents, and improving cash replenishment planning.
              </p>

              <div className="developer-cta">
                <a
                  href="https://www.linkedin.com/in/lakshay-aggarwal06/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-linkedin"
                >
                  <svg
                    className="linkedin-icon"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.45a1.64 1.64 0 1 0 0 3.28 1.64 1.64 0 0 0 0-3.28z" />
                  </svg>
                  <span>Connect on LinkedIn</span>
                  <ExternalLink size={14} className="external-icon" />
                </a>
              </div>
            </div>
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
