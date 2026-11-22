import axios from "axios";

// Base API URL configured from environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

const DEMO_READ_ROUTES = [
  /^\/dashboard\/kpis$/,
  /^\/dashboard\/demand$/,
  /^\/dashboard\/refill-atms$/,
  /^\/plan$/,
  /^\/plan\/route$/,
  /^\/model\/metrics$/,
  /^\/alerts$/,
  /^\/atms$/,
  /^\/forecast\/atm\/[A-Za-z0-9_-]+$/,
  /^\/forecast\/region$/,
  /^\/analytics$/,
];

// Attach Bearer JWT token to every request if available
api.interceptors.request.use(
  (config) => {
    if (localStorage.getItem("koshflow_demo") === "true") {
      const method = (config.method || "get").toLowerCase();
      const requestPath = (config.url || "").split("?")[0];
      if (requestPath.startsWith("/api/")) {
        if (method !== "get") {
          return Promise.reject(new Error("Public demo access is read-only."));
        }
        config.headers.Authorization = undefined;
        return config;
      }
      if (method !== "get" || !DEMO_READ_ROUTES.some((route) => route.test(requestPath))) {
        return Promise.reject(new Error("This request is not available in read-only demo mode."));
      }
      config.url = `/demo${config.url}`;
      config.headers.Authorization = undefined;
      return config;
    }

    const token = localStorage.getItem("koshflow_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Global response interceptor for token expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response &&
      error.response.status === 401 &&
      localStorage.getItem("koshflow_demo") !== "true"
    ) {
      localStorage.removeItem("koshflow_token");
      localStorage.removeItem("koshflow_user");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
