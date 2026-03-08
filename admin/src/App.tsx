import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { adminPing, clearToken, getMe, getToken, login, setToken, type MeResponse } from "./lib/api";
import ExamEditorPage from "./pages/ExamEditorPage";
import ExamsListPage from "./pages/ExamsListPage";

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
    <main>
      <h1>ExamShield Admin</h1>

      {!me && (
        <form className="login-form" onSubmit={onLogin}>
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
        </form>
      )}

      {error && <p className="error">Error: {error}</p>}

      {me && (
        <>
          <section className="panel">
            <div className="toolbar">
              <p>
                Logged in as <strong>{me.username}</strong> ({me.role})
              </p>
              <div className="actions">
                <button type="button" onClick={() => void onAdminPing()}>
                  Admin Ping
                </button>
                <button type="button" onClick={onLogout}>
                  Logout
                </button>
              </div>
            </div>
            {pingResult && <pre>{pingResult}</pre>}
          </section>

          <Routes>
            <Route path="/" element={<ExamsListPage onAuthError={handleAuthError} />} />
            <Route path="/exams/:examId" element={<ExamEditorPage onAuthError={handleAuthError} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </>
      )}
    </main>
  );
}

export default App;
