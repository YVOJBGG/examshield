import { getToken } from "./api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const RECONNECT_DELAY_MS = 3000;

export type MonitoringConnectionState = "connecting" | "connected" | "disconnected";

export type SnapshotAttempt = {
  attempt_id: string;
  username: string;
  exam_id: string;
  status: string;
  last_event: string;
  last_update: string;
};

export type MonitoringEventPayload = {
  event_type: string;
  timestamp: string;
  user_id: string;
  username: string;
  exam_id: string;
  attempt_id: string;
  status: string;
  message?: string | null;
};

export type MonitoringMessage =
  | { type: "snapshot"; attempts: SnapshotAttempt[] }
  | { type: "event"; data: MonitoringEventPayload };

type Callbacks = {
  onOpen: () => void;
  onMessage: (message: MonitoringMessage) => void;
  onClose: (event: CloseEvent) => void;
  onError: () => void;
};

function toMonitoringWebSocketUrl(baseUrl: string, token: string): string {
  const url = new URL(baseUrl);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${url.host}/ws/admin/monitor?token=${encodeURIComponent(token)}`;
}

export class MonitoringSocket {
  private ws: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private manuallyClosed = false;
  private readonly callbacks: Callbacks;

  constructor(callbacks: Callbacks) {
    this.callbacks = callbacks;
  }

  connect(): void {
    const token = getToken();
    if (!token) {
      return;
    }

    this.clearReconnect();
    this.manuallyClosed = false;
    this.ws = new WebSocket(toMonitoringWebSocketUrl(API_BASE_URL, token));

    this.ws.onopen = () => {
      this.callbacks.onOpen();
    };

    this.ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as MonitoringMessage;
        this.callbacks.onMessage(parsed);
      } catch {
        // Ignore malformed messages to keep stream resilient.
      }
    };

    this.ws.onerror = () => {
      this.callbacks.onError();
    };

    this.ws.onclose = (event) => {
      this.callbacks.onClose(event);
      if (!this.manuallyClosed && event.code !== 1008 && getToken()) {
        this.reconnectTimer = window.setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
      }
    };
  }

  disconnect(): void {
    this.manuallyClosed = true;
    this.clearReconnect();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private clearReconnect(): void {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
