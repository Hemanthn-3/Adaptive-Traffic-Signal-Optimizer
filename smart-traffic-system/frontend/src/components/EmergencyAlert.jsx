import React, { useState } from "react";
import { deactivateEmergency } from "../api/trafficApi";

export default function EmergencyAlert({ event }) {
  const [clearing, setClearing] = useState(false);

  if (!event) return null;

  const route = Array.isArray(event.route) ? event.route : JSON.parse(event.route || "[]");

  const handleClear = async () => {
    setClearing(true);
    try {
      await deactivateEmergency(event.event_id);
    } catch (e) {
      console.error("Failed to clear corridor:", e);
    } finally {
      setClearing(false);
    }
  };

  const eta = event.estimated_arrival
    ? new Date(event.estimated_arrival).toLocaleTimeString()
    : "Unknown";

  return (
    <div
      className="relative w-full px-6 py-4 flex items-center justify-between gap-4 overflow-hidden"
      style={{
        background: "linear-gradient(90deg, #1a0000 0%, #2d0000 50%, #1a0000 100%)",
        borderTop: "2px solid #ff4444",
        borderBottom: "2px solid #ff4444",
        animation: "emergencyPulse 1.5s ease-in-out infinite",
      }}
    >
      {/* Animated left stripe */}
      <div
        className="absolute left-0 top-0 h-full w-1"
        style={{ background: "#ff4444", animation: "flashBar 1s step-end infinite" }}
      />

      <div className="flex items-center gap-4 min-w-0">
        <span className="text-3xl flex-shrink-0" role="img" aria-label="emergency">🚨</span>
        <div className="min-w-0">
          <p className="font-bold text-red-400 text-lg leading-tight tracking-wide">
            AMBULANCE CORRIDOR ACTIVE
          </p>
          <p className="text-sm text-red-300 truncate">
            <span className="font-mono font-bold text-white">{event.vehicle_id}</span>
            {" · "}
            <span className="text-gray-400">Route: </span>
            {route.join(" → ")}
            {" · "}
            <span className="text-gray-400">ETA: </span>
            <span className="font-mono text-amber-400">{eta}</span>
          </p>
        </div>
      </div>

      <button
        onClick={handleClear}
        disabled={clearing}
        className="flex-shrink-0 px-5 py-2 rounded-lg font-bold text-sm uppercase tracking-wider transition-all"
        style={{
          background: clearing ? "#3d0000" : "#ff4444",
          color: "#fff",
          border: "1px solid #ff6666",
          cursor: clearing ? "not-allowed" : "pointer",
          opacity: clearing ? 0.7 : 1,
        }}
      >
        {clearing ? "Clearing…" : "Clear Corridor"}
      </button>

      <style>{`
        @keyframes emergencyPulse {
          0%, 100% { box-shadow: 0 0 20px rgba(255,68,68,0.3); }
          50%       { box-shadow: 0 0 40px rgba(255,68,68,0.6); }
        }
        @keyframes flashBar {
          0%, 49% { opacity: 1; }
          50%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}
