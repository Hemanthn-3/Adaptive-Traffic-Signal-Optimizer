import axios from "axios";
import { API_BASE_URL } from "../config";

const api = axios.create({ baseURL: API_BASE_URL, timeout: 15000 });

// ── Intersections ─────────────────────────────────────────────────────────────
export const fetchIntersections = () =>
  api.get("/api/traffic/intersections").then((r) => r.data);

// ── Density ───────────────────────────────────────────────────────────────────
export const fetchLatestDensity = (intersectionId) =>
  api.get(`/api/traffic/density`, { params: { intersection_id: intersectionId } }).then((r) => r.data);

export const fetchDensityHistory = (intersectionId, limit = 100) =>
  api.get("/api/traffic/density/history", { params: { lane_id: intersectionId, limit } }).then((r) => r.data);

// ── Signals ───────────────────────────────────────────────────────────────────
export const fetchSignalState = (intersectionId) =>
  api.get(`/api/signals/${intersectionId}`).then((r) => r.data);

export const fetchAllSignalStates = () =>
  api.get("/api/signals/all").then((r) => r.data);

// ── Emergency ─────────────────────────────────────────────────────────────────
export const activateEmergency = (vehicleId, vehicleType, route) =>
  api.post("/api/emergency/activate", { vehicle_id: vehicleId, vehicle_type: vehicleType, route }).then((r) => r.data);

export const deactivateEmergency = (eventId) =>
  api.post("/api/emergency/deactivate", { event_id: eventId }).then((r) => r.data);

export const fetchActiveEmergencies = () =>
  api.get("/api/emergency/active").then((r) => r.data);

export const simulateEmergency = (vehicleId = "AMB-SIM-001") =>
  api.post("/api/emergency/simulate", { vehicle_id: vehicleId }).then((r) => r.data);

// ── Video upload ──────────────────────────────────────────────────────────────
export const uploadVideo = (file, intersectionId) => {
  const form = new FormData();
  form.append("file", file);
  form.append("intersection_id", intersectionId);
  return api.post("/api/traffic/video/process", form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300000, // 5 minutes
  }).then((r) => r.data);
};

export default api;
