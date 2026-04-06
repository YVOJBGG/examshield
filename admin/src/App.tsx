import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { adminPing, clearToken, getMe, getToken, login, setToken, type MeResponse } from "./lib/api";
import ExamAnalyticsPage from "./pages/ExamAnalyticsPage";
import ExamEditorPage from "./pages/ExamEditorPage";
import ExamsListPage from "./pages/ExamsListPage";
import ExamSubmissionsPage from "./pages/ExamSubmissionsPage";
import LiveMonitoringPage from "./pages/LiveMonitoringPage";

function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [pingResult, setPingResult] = useState<string | null>(null);

  useEffect(() => {
    async function loadMeIfTokenExists() {
      const token = getToken();
      if (!token) {
        return;
      }

      try {
        const currentUser = await getMe();
        setMe(currentUser);
      } catch {
        clearToken();
      }
    }
    void loadMeIfTokenExists();
  }, []);

  async function onLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPingResult(null);
    setSubmitting(true);

    try {
      const response = await login(username, password);
      setToken(response.access_token);
      const currentUser = await getMe();
      setMe(currentUser);
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function onAdminPing() {
    setPingResult(null);
    setError(null);

    try {
      const result = await adminPing();
      setPingResult(JSON.stringify(result));
    } catch (err) {
      setPingResult(`Error: ${err instanceof Error ? err.message : "Request failed"}`);
    }
  }

  function onLogout() {
    clearToken();
    setMe(null);
    setPingResult(null);
    setError(null);
  }

  function handleAuthError(message: string) {
    setError(message);
  }

  return (
    <main className="app-shell">
      {!me ? (
        <section className="auth-shell">
          <div className="auth-hero">
            <span className="eyebrow">ExamShield Admin</span>
            <h1>Secure exam operations in one focused workspace.</h1>
            <p>
              Manage exams, monitor live activity, and review submitted attempts from a single
              professional dashboard.
            </p>
          </div>

          <form className="login-form" onSubmit={onLogin}>
            <div className="section-heading">
              <div>
                <span className="eyebrow">Sign In</span>
                <h2>Admin access</h2>
              </div>
            </div>

            <label htmlFor="username">Username</label>
            <input
              id="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="admin"
              required
            />

            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="********"
              required
            />

            <button type="submit" disabled={submitting}>
              {submitting ? "Logging in..." : "Login"}
            </button>

            {error && <p className="error">Error: {error}</p>}
          </form>
        </section>
      ) : (
        <>
          <header className="topbar">
            <div>
              <span className="eyebrow">ExamShield Admin</span>
              <h1>Operations Dashboard</h1>
              <p className="page-intro">
                Manage assessments, monitor live attempts, and review submissions with consistent
                admin workflows.
              </p>
            </div>

            <div className="topbar-actions">
              <div className="profile-chip">
                <span className="profile-avatar">{me.username.slice(0, 1).toUpperCase()}</span>
                <div>
                  <strong>{me.username}</strong>
                  <p>{me.role}</p>
                </div>
              </div>
              <div className="actions">
                <button type="button" className="secondary-button" onClick={() => void onAdminPing()}>
                  Admin Ping
                </button>
                <button type="button" onClick={onLogout}>
                  Logout
                </button>
              </div>
            </div>
          </header>

          <nav className="nav-shell">
            <div className="nav-links">
              <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                Exams
              </NavLink>
              <NavLink
                to="/monitoring"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              >
                Live Monitoring
              </NavLink>
            </div>
            <span className="status-pill">Admin workspace</span>
          </nav>

          {error && <p className="error banner-error">Error: {error}</p>}
          {pingResult && <pre>{pingResult}</pre>}

          <div className="page-stack">
            <Routes>
              <Route path="/" element={<ExamsListPage onAuthError={handleAuthError} />} />
              <Route path="/monitoring" element={<LiveMonitoringPage onAuthError={handleAuthError} />} />
              <Route path="/exams/new" element={<ExamEditorPage onAuthError={handleAuthError} />} />
              <Route path="/exams/:examId" element={<ExamEditorPage onAuthError={handleAuthError} />} />
              <Route
                path="/exams/:examId/analytics"
                element={<ExamAnalyticsPage onAuthError={handleAuthError} />}
              />
              <Route
                path="/exams/:examId/submissions"
                element={<ExamSubmissionsPage onAuthError={handleAuthError} />}
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </>
      )}
    </main>
  );
}

export default App;
