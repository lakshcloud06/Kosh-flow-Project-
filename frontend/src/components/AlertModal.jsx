import React from "react";
import { X, AlertTriangle, AlertCircle, CheckCircle } from "lucide-react";

export default function AlertModal({ isOpen, onClose, alerts }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <AlertTriangle color="#DC2626" size={22} />
            <h3>Active Cash Demand & Cash-Out Alerts ({alerts.length})</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {alerts.length === 0 ? (
            <p className="empty-text">No active alerts. All ATMs operating with normal cash buffer.</p>
          ) : (
            <div className="alert-list">
              {alerts.map((alert) => (
                <div key={alert.id} className={`alert-card alert-risk-${alert.risk_level}`}>
                  <div className="alert-badge-col">
                    <span className={`risk-badge badge-${alert.risk_level}`}>
                      {alert.risk_level.toUpperCase()}
                    </span>
                  </div>
                  <div className="alert-info-col">
                    <div className="alert-header-row">
                      <strong className="alert-atm">{alert.atm_id}</strong>
                      <span className="alert-time">{alert.created_at || "Recent"}</span>
                    </div>
                    <p className="alert-msg">{alert.message}</p>
                    <div className="alert-meta">
                      <span>Cash Left: ₹{(alert.cash_left / 100000).toFixed(2)} L</span>
                      <span>Run-out: ~{alert.predicted_runout_days} days</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
