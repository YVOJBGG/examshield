const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_KEY = "access_token";

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type MeResponse = {
  id: string;
  username: string;
  role: string;
};

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function authFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(`${API_BASE_URL}${input}`, { ...init, headers });
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error("Login failed");
  }

  return response.json() as Promise<LoginResponse>;
}

export async function getMe(): Promise<MeResponse> {
  const response = await authFetch("/auth/me");

  if (!response.ok) {
    throw new Error("Could not load current user");
  }

  return response.json() as Promise<MeResponse>;
}

export async function adminPing(): Promise<unknown> {
  const response = await authFetch("/admin/ping");
  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = typeof body === "object" && body && "detail" in body ? String(body.detail) : "Admin ping failed";
    throw new Error(detail);
  }

  return body;
}
