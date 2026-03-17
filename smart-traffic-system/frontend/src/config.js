const trimTrailingSlashes = (value) => value.replace(/\/+$/, "");

const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const browserApiBase = typeof window !== "undefined" ? window.location.origin : "http://localhost:8000";

export const API_BASE_URL = trimTrailingSlashes(rawApiBaseUrl || browserApiBase);

const rawWsUrl = import.meta.env.VITE_WS_URL?.trim();
const browserWsBase =
  typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`
    : "ws://localhost:8000/ws";

export const WS_URL = rawWsUrl || browserWsBase;

export function apiUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}
