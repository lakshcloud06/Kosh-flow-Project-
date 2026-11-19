import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import PlanPage from "./pages/PlanPage";
import ModelPage from "./pages/ModelPage";
import AboutPage from "./pages/AboutPage";
import DemoNetworkPage from "./pages/DemoNetworkPage";
import DemoAnalyticsPage from "./pages/DemoAnalyticsPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Authentication Route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Application Routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/plan" element={<PlanPage />} />
              <Route path="/model" element={<ModelPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route element={<DemoOnlyRoute />}>
                <Route path="/demo/network" element={<DemoNetworkPage />} />
                <Route path="/demo/analytics" element={<DemoAnalyticsPage />} />
              </Route>
            </Route>
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

function DemoOnlyRoute() {
  const { isDemo } = useAuth();
  return isDemo ? <Outlet /> : <Navigate to="/" replace />;
}
