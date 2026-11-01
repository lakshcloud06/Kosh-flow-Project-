import React, { useState, useEffect } from "react";
import { Bell, LogOut, User as UserIcon } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api from "../api/client";
import AlertModal from "./AlertModal";

export default function TopNavbar() {
  const { user, logout } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await api.get("/alerts");
        setAlerts(res.data);
      } catch (err) {
        console.error("Failed to load alerts:", err);
      }
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const latestAlert = alerts.length > 0 ? alerts[0].message : "All network ATMs operating within safe cash reserves";

  return (
    <>
      <header className="top-navbar">
        {/* Notification Bar */}
        <div className="notification-bar">
          <div className="bell-container" onClick={() => setModalOpen(true)} title="View active alerts">
            <Bell size={18} className="bell-icon" />
            {alerts.length > 0 && (
              <span className="alert-count-badge">{alerts.length}</span>
            )}
          </div>
          <span className="notification-text">
            <strong>Alert:</strong> {latestAlert}
          </span>
          <button
            type="button"
            className="view-all-link"
            onClick={() => setModalOpen(true)}
          >
            View all
          </button>
        </div>

        {/* User Profile and Logout */}
        <div className="nav-user-actions">
          <div className="user-info-pill">
            <div className="user-avatar">
              <UserIcon size={16} />
            </div>
            <span className="user-name">{user?.full_name || "Operator"}</span>
          </div>
          <button
            type="button"
            className="logout-button"
            onClick={logout}
            title="Sign out"
          >
            <LogOut size={16} />
            <span>Sign out</span>
          </button>
        </div>
      </header>

      <AlertModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        alerts={alerts}
      />
    </>
  );
}
