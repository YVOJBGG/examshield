import { useEffect, useMemo, useRef, useState } from "react";

import { getToken, listAttemptViolations, type ViolationListItem } from "../lib/api";
import {
  MonitoringSocket,
  type MonitoringConnectionState,
  type MonitoringEventPayload,
  type SnapshotAttempt,
  type ViolationPayload,
} from "../lib/monitoring";

type AttemptRow = {
  username: string;
  exam_id: string;
  attempt_id: string;
  status: string;
  last_event: string;
  last_update: string;
  alert_count: number;
  has_alerts: boolean;
  last_violation_type: string | null;
  last_violation_at: string | null;
};

type ToastItem = {
  id: number;
  message: string;
};

function toAttemptRowFromSnapshot(item: SnapshotAttempt): AttemptRow {
  return {
    username: item.username,
    exam_id: item.exam_id,
    attempt_id: item.attempt_id,
    status: item.status,
    last_event: item.last_event,
    last_update: item.last_update,
    alert_count: item.alert_count ?? 0,
    has_alerts: item.has_alerts ?? false,
    last_violation_type: item.last_violation_type ?? null,
    last_violation_at: item.last_violation_at ?? null,
  };
}

function toAttemptRowFromEvent(item: MonitoringEventPayload, existing?: AttemptRow): AttemptRow {
  return {
    username: item.username,
    exam_id: item.exam_id,
    attempt_id: item.attempt_id,
    status: item.status,
    last_event: item.event_type,
    last_update: item.timestamp,
    alert_count: existing?.alert_count ?? 0,
    has_alerts: existing?.has_alerts ?? false,
    last_violation_type: existing?.last_violation_type ?? null,
    last_violation_at: existing?.last_violation_at ?? null,
  };
}

function toAttemptRowFromViolation(item: ViolationPayload, existing?: AttemptRow): AttemptRow {
  return {
    username: item.username,
    exam_id: item.exam_id,
    attempt_id: item.attempt_id,
    status: item.status,
    last_event: "violation",
    last_update: item.created_at,
    alert_count: (existing?.alert_count ?? 0) + 1,
    has_alerts: true,
    last_violation_type: item.type,
    last_violation_at: item.created_at,
  };
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function LiveMonitoringPage() {
  const [connection, setConnection] = useState<MonitoringConnectionState>("connecting");
  const [attemptMap, setAttemptMap] = useState<Record<string, AttemptRow>>({});
  const [lastMessageAt, setLastMessageAt] = useState<string | null>(null);
  const [socketError, setSocketError] = useState<string | null>(null);
  const [showOnlyAlerts, setShowOnlyAlerts] = useState(false);
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);
  const [violations, setViolations] = useState<ViolationListItem[]>([]);
  const [violationsLoading, setViolationsLoading] = useState(false);
  const [violationsError, setViolationsError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const toastTimersRef = useRef<number[]>([]);
  const selectedAttemptIdRef = useRef<string | null>(null);

  const hasToken = Boolean(getToken());

  function pushToast(message: string) {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((prev) => [...prev, { id, message }]);
    const timer = window.setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id));
      toastTimersRef.current = toastTimersRef.current.filter((item) => item !== timer);
    }, 3500);
    toastTimersRef.current.push(timer);
  }

  useEffect(() => {
    selectedAttemptIdRef.current = selectedAttemptId;
  }, [selectedAttemptId]);

  useEffect(() => {
    return () => {
      toastTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      toastTimersRef.current = [];
    };
  }, []);

  useEffect(() => {
    if (!hasToken) {
      setConnection("disconnected");
      return;
    }

    setConnection("connecting");
    setSocketError(null);

    const socket = new MonitoringSocket({
      onOpen: () => {
        setConnection("connected");
        setSocketError(null);
      },
      onMessage: (message) => {
        setLastMessageAt(new Date().toISOString());
        if (message.type === "snapshot") {
          setAttemptMap(
            message.attempts.reduce<Record<string, AttemptRow>>((acc, item) => {
              acc[item.attempt_id] = toAttemptRowFromSnapshot(item);
              return acc;
            }, {}),
          );
          return;
        }

        if (message.type === "event") {
          setAttemptMap((prev) => ({
            ...prev,
            [message.data.attempt_id]: toAttemptRowFromEvent(message.data, prev[message.data.attempt_id]),
          }));
          return;
        }

        pushToast(`Violation: ${message.data.username} - ${message.data.type}`);
        if (selectedAttemptIdRef.current === message.data.attempt_id) {
          setViolations((prev) => [
            {
              id: message.data.id,
              attempt_id: message.data.attempt_id,
              type: message.data.type,
              details: message.data.details ?? null,
              created_at: message.data.created_at,
            },
            ...prev,
          ]);
        }
        setAttemptMap((prev) => ({
          ...prev,
          [message.data.attempt_id]: toAttemptRowFromViolation(
            message.data,
            prev[message.data.attempt_id],
          ),
        }));
      },
      onClose: (event) => {
        setConnection("disconnected");
        if (event.code === 1008) {
          setSocketError(event.reason || "WebSocket authorization failed. Please login as admin.");
        }
      },
      onError: () => {
        setConnection("disconnected");
        setSocketError("Live monitoring connection error.");
      },
    });

    socket.connect();
    return () => {
      socket.disconnect();
    };
  }, [hasToken]);

  useEffect(() => {
    if (!selectedAttemptId || !hasToken) {
      setViolations([]);
      setViolationsError(null);
      setViolationsLoading(false);
      return;
    }

    let cancelled = false;
    setViolationsLoading(true);
    setViolationsError(null);

    void listAttemptViolations(selectedAttemptId)
      .then((items) => {
        if (cancelled) {
          return;
        }
        setViolations(items);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setViolationsError(error instanceof Error ? error.message : "Could not load violations");
        setViolations([]);
      })
      .finally(() => {
        if (!cancelled) {
          setViolationsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [hasToken, selectedAttemptId]);

  const rows = useMemo(
    () =>
      Object.values(attemptMap)
        .filter((row) => !showOnlyAlerts || row.has_alerts)
        .sort((a, b) => b.last_update.localeCompare(a.last_update)),
    [attemptMap, showOnlyAlerts],
  );

  const selectedRow = selectedAttemptId ? attemptMap[selectedAttemptId] ?? null : null;
  const totalAttempts = rows.length;
  const alertRows = rows.filter((row) => row.has_alerts).length;
  const totalAlerts = rows.reduce((sum, row) => sum + row.alert_count, 0);
  const connectionLabel =
    connection === "connected" ? "Connected" : connection === "connecting" ? "Connecting" : "Disconnected";

  if (!hasToken) {
    return (
      <section className="panel">
        <h2>Live Monitoring</h2>
        <p>Please login first to use live monitoring.</p>
      </section>
    );
  }

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <span className="eyebrow">Monitoring</span>
          <h2>Live exam activity</h2>
          <p className="page-intro">
            Track active attempts, surface alert activity quickly, and inspect per-attempt
            violations without losing sight of the main monitoring feed.
          </p>
        </div>
      </div>

      <div className="toast-stack" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className="toast">
            {toast.message}
          </div>
        ))}
      </div>

      <div className="stats-grid">
        <article className="stat-card">
          <span className="stat-label">Connection</span>
          <strong>{connectionLabel}</strong>
          <p>WebSocket status for the live monitoring stream.</p>
        </article>
        <article className="stat-card">
          <span className="stat-label">Tracked attempts</span>
          <strong>{totalAttempts}</strong>
          <p>Attempts currently visible in this monitoring session.</p>
        </article>
        <article className="stat-card">
          <span className="stat-label">Rows with alerts</span>
          <strong>{alertRows}</strong>
          <p>Attempt rows currently flagged with one or more violations.</p>
        </article>
        <article className="stat-card">
          <span className="stat-label">Alert count</span>
          <strong>{totalAlerts}</strong>
          <p>Total violation count accumulated across visible attempts.</p>
        </article>
      </div>

      <div className="monitoring-layout">
        <section className="panel monitoring-table-panel">
          <div className="section-heading">
            <div>
              <h3>Attempts overview</h3>
              <p>Live state for currently tracked attempts, including their latest monitoring signal.</p>
            </div>
            <div className="monitoring-toolbar">
              <div className="status-summary">
                <span className={`status-dot ${connection}`} />
                <strong>{connectionLabel}</strong>
              </div>
              <span className="status-pill">Last message {formatTimestamp(lastMessageAt)}</span>
            </div>
          </div>

          <label className="monitoring-filter">
            <input
              type="checkbox"
              checked={showOnlyAlerts}
              onChange={(event) => setShowOnlyAlerts(event.target.checked)}
            />
            Show only attempts with alerts
          </label>

          {socketError && <p className="error">Error: {socketError}</p>}

          {rows.length === 0 ? (
            <p className="state-text">{showOnlyAlerts ? "No attempts with alerts." : "No active attempts yet."}</p>
          ) : (
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Exam ID</th>
                    <th>Attempt ID</th>
                    <th>Status</th>
                    <th>Alerts</th>
                    <th>Latest Violation</th>
                    <th>Last Update</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr
                      key={row.attempt_id}
                      className={[
                        row.has_alerts ? "attempt-row-alert" : "",
                        selectedAttemptId === row.attempt_id ? "attempt-row-selected" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    >
                      <td>
                        <strong>{row.username}</strong>
                      </td>
                      <td className="mono">{row.exam_id}</td>
                      <td className="mono">{row.attempt_id}</td>
                      <td>
                        <span className="status-pill">{row.status}</span>
                      </td>
                      <td>
                        <span className={row.has_alerts ? "alert-badge" : "neutral-badge"}>
                          {row.alert_count}
                        </span>
                      </td>
                      <td>{row.last_violation_type ?? "-"}</td>
                      <td>{formatTimestamp(row.last_violation_at ?? row.last_update)}</td>
                      <td>
                        <button type="button" className="secondary-button" onClick={() => setSelectedAttemptId(row.attempt_id)}>
                          View Violations
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <aside className="panel monitoring-detail-panel">
          <div className="section-heading">
            <div>
              <h3>Violation details</h3>
              <p>Selected attempt history with timestamps and event descriptions.</p>
            </div>
          </div>
          {!selectedRow ? (
            <p className="state-text">Select an attempt to inspect its violation history.</p>
          ) : (
            <>
              <div className="review-meta-card">
                <div className="review-meta">
                  <p>
                    <span>Student</span>
                    <strong>{selectedRow.username}</strong>
                  </p>
                  <p>
                    <span>Attempt</span>
                    <strong className="mono">{selectedRow.attempt_id}</strong>
                  </p>
                  <p>
                    <span>Status</span>
                    <strong>{selectedRow.status}</strong>
                  </p>
                  <p>
                    <span>Alerts</span>
                    <strong>{selectedRow.alert_count}</strong>
                  </p>
                </div>
              </div>
              {violationsLoading && <p className="state-text">Loading violations...</p>}
              {violationsError && <p className="error">Error: {violationsError}</p>}
              {!violationsLoading && !violationsError && violations.length === 0 && (
                <p className="state-text">No violations recorded for this attempt.</p>
              )}
              {!violationsLoading && !violationsError && violations.length > 0 && (
                <div className="violation-list">
                  {violations.map((item) => (
                    <article key={item.id} className="violation-card">
                      <div className="violation-card-header">
                        <strong>{item.type}</strong>
                        <span>{formatTimestamp(item.created_at)}</span>
                      </div>
                      <p>{item.details || "No details provided."}</p>
                    </article>
                  ))}
                </div>
              )}
            </>
          )}
        </aside>
      </div>
    </section>
  );
}

export default LiveMonitoringPage;
