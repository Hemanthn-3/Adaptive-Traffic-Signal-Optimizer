import React, { useEffect, useRef, useState } from "react";

// Bengaluru intersections
const INTERSECTIONS = [
  { id: "INT-01", name: "MG Road & Brigade Road",  lat: 12.9757, lng: 77.6011 },
  { id: "INT-02", name: "Silk Board Junction",      lat: 12.9174, lng: 77.6229 },
  { id: "INT-03", name: "KR Circle",                lat: 12.9762, lng: 77.5713 },
  { id: "INT-04", name: "Hebbal Flyover",           lat: 13.0352, lng: 77.5969 },
  { id: "INT-05", name: "Marathahalli Bridge",      lat: 12.9591, lng: 77.6974 },
  { id: "INT-06", name: "Electronic City",          lat: 12.8399, lng: 77.6770 },
  { id: "INT-07", name: "Whitefield Main Road",     lat: 12.9698, lng: 77.7499 },
  { id: "INT-08", name: "Jayanagar 4th Block",      lat: 12.9250, lng: 77.5938 },
];

const LEVEL_COLORS = {
  low:      "#00ff88",
  medium:   "#f59e0b",
  high:     "#f97316",
  critical: "#ef4444",
};

function getLevelColor(density) {
  if (!density) return "#3b82f6";
  if (density <= 30) return LEVEL_COLORS.low;
  if (density <= 60) return LEVEL_COLORS.medium;
  if (density <= 80) return LEVEL_COLORS.high;
  return LEVEL_COLORS.critical;
}

function getLevel(density) {
  if (!density) return "low";
  if (density <= 30) return "low";
  if (density <= 60) return "medium";
  if (density <= 80) return "high";
  return "critical";
}

export default function CityMap({ intersectionData = {}, isEmergency = false, emergencyRoute = [], onIntersectionSelect }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const routeLineRef = useRef(null);
  const [showRoute, setShowRoute] = useState(true);
  const [L, setL] = useState(null);

  // Dynamically load Leaflet
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.L) {
      setL(window.L);
      return;
    }

    // Load CSS
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    document.head.appendChild(link);

    // Load JS
    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.onload = () => setL(window.L);
    document.head.appendChild(script);
  }, []);

  // Initialize map when L is loaded
  useEffect(() => {
    if (!L || !mapRef.current || mapInstanceRef.current) return;

    const map = L.map(mapRef.current, {
      zoomControl: false,
      attributionControl: false,
    }).setView([12.97, 77.62], 12);

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      { subdomains: "abcd", maxZoom: 20 }
    ).addTo(map);

    L.control.zoom({ position: "bottomright" }).addTo(map);

    mapInstanceRef.current = map;

    // Fit all markers
    const bounds = INTERSECTIONS.map(i => [i.lat, i.lng]);
    map.fitBounds(bounds, { padding: [40, 40] });

    // Add markers
    INTERSECTIONS.forEach(inter => {
      const data = intersectionData[inter.id] || {};
      const density = (data.lane_a_density + data.lane_b_density) / 2 || 0;
      const color = getLevelColor(density);
      const radius = Math.max(10, Math.min(24, 10 + (density / 100) * 14));

      const marker = L.circleMarker([inter.lat, inter.lng], {
        radius,
        color: "transparent",
        fillColor: color,
        fillOpacity: 0.85,
        weight: 2,
      }).addTo(map);

      const popup = L.popup({ className: "traffic-popup", closeButton: false })
        .setContent(buildPopup(inter, data));

      marker.bindPopup(popup);
      marker.on("click", () => {
        if (onIntersectionSelect) onIntersectionSelect(inter);
      });

      markersRef.current[inter.id] = marker;
    });
  }, [L]);

  // Update markers when data changes
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    INTERSECTIONS.forEach(inter => {
      const marker = markersRef.current[inter.id];
      if (!marker) return;
      const data = intersectionData[inter.id] || {};
      const density = (data.lane_a_density + data.lane_b_density) / 2 || 0;
      const color = getLevelColor(density);
      const radius = Math.max(10, Math.min(24, 10 + (density / 100) * 14));

      marker.setStyle({ fillColor: color, radius });
      marker.setPopupContent(buildPopup(inter, data));
    });
  }, [intersectionData]);

  // Draw emergency route
  useEffect(() => {
    if (!L || !mapInstanceRef.current) return;

    if (routeLineRef.current) {
      routeLineRef.current.remove();
      routeLineRef.current = null;
    }

    if (isEmergency && showRoute && emergencyRoute.length > 1) {
      const coords = emergencyRoute
        .map(id => INTERSECTIONS.find(i => i.id === id))
        .filter(Boolean)
        .map(i => [i.lat, i.lng]);

      if (coords.length > 1) {
        routeLineRef.current = L.polyline(coords, {
          color: "#ef4444",
          weight: 4,
          opacity: 0.8,
          dashArray: "10, 10",
          lineCap: "round",
        }).addTo(mapInstanceRef.current);
      }
    }
  }, [L, isEmergency, emergencyRoute, showRoute]);

  const fitAll = () => {
    if (!mapInstanceRef.current) return;
    const bounds = INTERSECTIONS.map(i => [i.lat, i.lng]);
    mapInstanceRef.current.fitBounds(bounds, { padding: [40, 40] });
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: 12, overflow: "hidden" }}>
      {/* Map container */}
      <div ref={mapRef} style={{ width: "100%", height: "100%" }} />

      {/* Controls overlay */}
      <div style={{
        position: "absolute",
        top: 12,
        left: 12,
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}>
        <button
          onClick={fitAll}
          style={{
            background: "rgba(13,21,37,0.9)",
            border: "1px solid #1e2d40",
            color: "#94a3b8",
            borderRadius: 8,
            padding: "6px 12px",
            fontSize: 12,
            cursor: "pointer",
            fontFamily: "Space Grotesk, sans-serif",
          }}
        >
          ⊡ Show All
        </button>
        <button
          onClick={() => setShowRoute(v => !v)}
          style={{
            background: showRoute ? "rgba(239,68,68,0.2)" : "rgba(13,21,37,0.9)",
            border: `1px solid ${showRoute ? "#ef4444" : "#1e2d40"}`,
            color: showRoute ? "#ef4444" : "#94a3b8",
            borderRadius: 8,
            padding: "6px 12px",
            fontSize: 12,
            cursor: "pointer",
            fontFamily: "Space Grotesk, sans-serif",
          }}
        >
          {showRoute ? "Hide Route" : "Show Route"}
        </button>
      </div>

      {/* Legend */}
      <div style={{
        position: "absolute",
        bottom: 40,
        left: 12,
        zIndex: 1000,
        background: "rgba(13,21,37,0.9)",
        border: "1px solid #1e2d40",
        borderRadius: 8,
        padding: "10px 14px",
      }}>
        <p style={{ color: "#94a3b8", fontSize: 10, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8, fontFamily: "Space Grotesk, sans-serif" }}>Density</p>
        {[
          { label: "Low ( ≤30%)", color: LEVEL_COLORS.low },
          { label: "Medium (≤60%)", color: LEVEL_COLORS.medium },
          { label: "High (≤80%)", color: LEVEL_COLORS.high },
          { label: "Critical (>80%)", color: LEVEL_COLORS.critical },
        ].map(({ label, color }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, flexShrink: 0 }} />
            <span style={{ color: "#94a3b8", fontSize: 11, fontFamily: "Space Grotesk, sans-serif" }}>{label}</span>
          </div>
        ))}
      </div>

      {/* Emergency indicator */}
      {isEmergency && (
        <div style={{
          position: "absolute",
          top: 12,
          right: 12,
          zIndex: 1000,
          background: "rgba(239,68,68,0.15)",
          border: "1px solid rgba(239,68,68,0.5)",
          borderRadius: 8,
          padding: "8px 16px",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444", animation: "pulse 1s infinite" }} />
          <span style={{ color: "#ef4444", fontSize: 12, fontWeight: 600, fontFamily: "Space Grotesk, sans-serif" }}>
            🚨 AMBULANCE CORRIDOR ACTIVE
          </span>
        </div>
      )}

      <style>{`
        .traffic-popup .leaflet-popup-content-wrapper {
          background: #111827;
          border: 1px solid #1e2d40;
          border-radius: 8px;
          color: #f1f5f9;
          font-family: 'Space Grotesk', sans-serif;
          font-size: 13px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }
        .traffic-popup .leaflet-popup-tip { background: #111827; }
        .leaflet-container { font-family: 'Space Grotesk', sans-serif; }
      `}</style>
    </div>
  );
}

function buildPopup(inter, data) {
  const aCount   = data.lane_a_count   || 0;
  const bCount   = data.lane_b_count   || 0;
  const aDensity = data.lane_a_density || 0;
  const bDensity = data.lane_b_density || 0;
  const aGreen   = data.lane_a_green   || 30;
  const bGreen   = data.lane_b_green   || 30;
  const level    = getLevel((aDensity + bDensity) / 2);
  const levelColor = LEVEL_COLORS[level] || "#3b82f6";

  return `
    <div style="min-width:200px; padding:4px 0;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span style="background:${levelColor};border-radius:4px;padding:2px 6px;font-size:10px;font-weight:600;color:#000;">${level.toUpperCase()}</span>
        <strong style="font-size:13px;">${inter.name}</strong>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;color:#94a3b8;">
        <div>
          <div style="color:#3b82f6;font-weight:600;margin-bottom:4px;">Lane A</div>
          <div>${aCount} vehicles</div>
          <div>${aDensity.toFixed(1)}% density</div>
          <div>🟢 ${aGreen}s green</div>
        </div>
        <div>
          <div style="color:#00ff88;font-weight:600;margin-bottom:4px;">Lane B</div>
          <div>${bCount} vehicles</div>
          <div>${bDensity.toFixed(1)}% density</div>
          <div>🟢 ${bGreen}s green</div>
        </div>
      </div>
      <div style="margin-top:8px;font-size:10px;color:#475569;">${inter.id} · ${inter.lat.toFixed(4)}, ${inter.lng.toFixed(4)}</div>
    </div>
  `;
}
