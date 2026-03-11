import { useEffect, useMemo, useState } from "react";

import { getToken } from "../lib/api";
import {
  MonitoringSocket,
  type MonitoringConnectionState,
  type MonitoringEventPayload,
  type SnapshotAttempt,
} from "../lib/monitoring";

type AttemptRow = {
  username: string;
  exam_id: string;
  attempt_id: string;
  status: string;
  last_event: string;
  last_update: string;
};

function toAttemptRowFromSnapshot(item: SnapshotAttempt): AttemptRow {
  return {
    username: item.username,
    exam_id: item.exam_id,
    attempt_id: item.attempt_id,
    status: item.status,
    last_event: item.last_event,
    last_update: item.last_update,
  };
}

function toAttemptRowFromEvent(item: MonitoringEventPayload): AttemptRow {
  return {
    username: item.username,
    exam_id: item.exam_id,
    attempt_id: item.attempt_id,
    status: item.status,
    last_event: item.event_type,
    last_update: item.timestamp,
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

  const hasToken = Boolean(getToken());

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

        setAttemptMap((prev) => ({
          ...prev,
          [message.data.attempt_id]: toAttemptRowFromEvent(message.data),
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

  const rows = useMemo(
    () => Object.values(attemptMap).sort((a, b) => b.last_update.localeCompare(a.last_update)),
    [attemptMap],
  );

  if (!hasToken) {
    return (
      <section className="panel">
        <h2>Live Monitoring</h2>
        <p>Please login first to use live monitoring.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>Live Monitoring</h2>

      <div className="monitoring-meta">
        <p>
          Connection: <strong>{connection === "connected" ? "Connected" : connection === "connecting" ? "Connecting" : "Disconnected"}</strong>
        </p>
        <p>
          Last message: <strong>{formatTimestamp(lastMessageAt)}</strong>
        </p>
      </div>

      {socketError && <p className="error">Error: {socketError}</p>}

      {rows.length === 0 ? (
        <p>No active attempts yet.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Exam ID</th>
              <th>Attempt ID</th>
              <th>Status</th>
              <th>Last Event</th>
              <th>Last Update</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.attempt_id}>
                <td>{row.username}</td>
                <td className="mono">{row.exam_id}</td>
                <td className="mono">{row.attempt_id}</td>
                <td>{row.status}</td>
                <td>{row.last_event}</td>
                <td>{formatTimestamp(row.last_update)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export default LiveMonitoringPage;
