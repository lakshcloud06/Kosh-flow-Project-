import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, Lock, Mail, ArrowRight, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      console.error("Login failed:", err);
      if (!err.response) {
        setError("Backend server is not reachable. Please start the backend at http://localhost:8000.");
      } else if (err.response.status === 401) {
        setError(err.response.data?.detail || "Invalid email or password. Please verify your credentials.");
      } else {
        setError(err.response.data?.detail || "An error occurred during authentication.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFillDemo = () => {
    setEmail("demo@koshflow.com");
    setPassword("password123");
    setError("");
  };

  return (
    <div className="login-viewport">
      <div className="login-card">
        <div className="login-header">
          <div className="login-icon-badge">
            <ShieldCheck size={36} color="#0F766E" />
          </div>
          <h1 className="login-title">Koshflow</h1>
          <p className="login-subtitle">
            ATM cash demand forecasting and smart refills.
          </p>
        </div>

        {error && (
          <div className="login-error-box">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <div className="input-with-icon">
              <Mail size={18} className="input-icon" />
              <input
                id="email"
                type="email"
                placeholder="name@bank.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="input-with-icon">
              <Lock size={18} className="input-icon" />
              <input
                id="password"
                type="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <span>Authenticating...</span>
            ) : (
              <>
                <span>Sign in</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="demo-credentials-card">
          <div className="demo-header">
            <span>Demo credentials:</span>
            <button
              type="button"
              className="demo-fill-btn"
              onClick={handleFillDemo}
            >
              Fill Demo Login
            </button>
          </div>
          <code className="demo-code">demo@koshflow.com / password123</code>
        </div>

        <div className="login-footer">
          <p className="secured-text">
            <Lock size={13} style={{ display: "inline", verticalAlign: "middle", marginRight: "4px" }} />
            Secured with JWT token authentication.
          </p>
        </div>
      </div>
    </div>
  );
}
