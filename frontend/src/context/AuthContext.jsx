import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../api/client";

const AuthContext = createContext(null);
const DEMO_USER = { full_name: "Lakshay" };

export const AuthProvider = ({ children }) => {
  const [isDemo, setIsDemo] = useState(() => localStorage.getItem("koshflow_demo") === "true");
  const [user, setUser] = useState(() => {
    if (localStorage.getItem("koshflow_demo") === "true") return DEMO_USER;
    const saved = localStorage.getItem("koshflow_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem("koshflow_token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verifyUser = async () => {
      if (localStorage.getItem("koshflow_demo") === "true") {
        localStorage.removeItem("koshflow_token");
        localStorage.removeItem("koshflow_user");
        setToken(null);
        setUser(DEMO_USER);
        setLoading(false);
        return;
      }

      const storedToken = localStorage.getItem("koshflow_token");
      if (storedToken) {
        try {
          const res = await api.get("/auth/me");
          setUser(res.data);
          localStorage.setItem("koshflow_user", JSON.stringify(res.data));
        } catch (err) {
          console.error("Session verification failed:", err);
          logout();
        }
      }
      setLoading(false);
    };
    verifyUser();
  }, []);

  const login = async (email, password) => {
    localStorage.removeItem("koshflow_demo");
    setIsDemo(false);
    const res = await api.post("/auth/login", { email, password });
    const { access_token, user: userData } = res.data;
    setToken(access_token);
    setUser(userData);
    localStorage.setItem("koshflow_token", access_token);
    localStorage.setItem("koshflow_user", JSON.stringify(userData));
    return userData;
  };

  const enterDemo = () => {
    localStorage.removeItem("koshflow_token");
    localStorage.removeItem("koshflow_user");
    localStorage.setItem("koshflow_demo", "true");
    setToken(null);
    setUser(DEMO_USER);
    setIsDemo(true);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setIsDemo(false);
    localStorage.removeItem("koshflow_token");
    localStorage.removeItem("koshflow_user");
    localStorage.removeItem("koshflow_demo");
  };

  return (
    <AuthContext.Provider value={{ user, token, isDemo, login, enterDemo, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
