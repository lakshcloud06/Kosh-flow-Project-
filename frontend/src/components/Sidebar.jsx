import React from "react";
import { NavLink } from "react-router-dom";
import { LayoutDashboard, Truck, Sliders, Info, ShieldCheck } from "lucide-react";

export default function Sidebar() {
  const navItems = [
    { name: "Dashboard", path: "/", icon: LayoutDashboard },
    { name: "Replenishment Plan", path: "/plan", icon: Truck },
    { name: "Model Settings", path: "/model", icon: Sliders },
    { name: "About Us", path: "/about", icon: Info },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">
          <ShieldCheck size={26} color="#2DD4BF" />
        </div>
        <div className="brand-text">
          <span className="brand-title">Koshflow</span>
          <span className="brand-tagline">ATM Cash Predictor</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                `nav-link ${isActive ? "nav-link-active" : ""}`
              }
            >
              <Icon size={18} className="nav-icon" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="system-status">
          <span className="status-dot"></span>
          <span className="status-text">Forecasting Engine Active</span>
        </div>
      </div>
    </aside>
  );
}
