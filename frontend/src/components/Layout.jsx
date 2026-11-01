import React from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopNavbar from "./TopNavbar";

export default function Layout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-wrapper">
        <TopNavbar />
        <main className="content-container">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
