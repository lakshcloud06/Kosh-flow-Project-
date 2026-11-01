import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", color: "#0F766E" }}>
        <div className="spinner"></div>
        <span style={{ marginLeft: "12px", fontWeight: "500" }}>Loading Koshflow...</span>
      </div>
    );
  }

  return token ? <Outlet /> : <Navigate to="/login" replace />;
}
