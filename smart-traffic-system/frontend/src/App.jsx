import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import Dashboard from "./components/Dashboard";
import Analytics from "./pages/Analytics";
import EmergencyAlert from "./components/EmergencyAlert";
import VehicleBreakdown from "./components/VehicleBreakdown";
import QueueInfo from "./components/QueueInfo";
import CityMap from "./components/CityMap";
import LiveFeed from "./components/LiveFeed";
import ModelFeed from "./components/ModelFeed";
import { useWebSocket } from "./hooks/useWebSocket";
import { fetchIntersections, simulateEmergency, uploadVideo } from "./api/trafficApi";
import { apiUrl } from "./config";

// ── Bengaluru intersections (fallback if API fails) ───────────────────────────
const DEFAULT_INTERSECTIONS = [
  { id: "INT-01", name: "MG Road & Brigade Road",  latitude: 12.9757, longitude: 77.6011 },
  { id: "INT-02", name: "Silk Board Junction",      latitude: 12.9174, longitude: 77.6229 },
  { id: "INT-03", name: "KR Circle",                latitude: 12.9762, longitude: 77.5713 },
  { id: "INT-04", name: "Hebbal Flyover",           latitude: 13.0352, longitude: 77.5969 },
  { id: "INT-05", name: "Marathahalli Bridge",      latitude: 12.9591, longitude: 77.6974 },
  { id: "INT-06", name: "Electronic City",          latitude: 12.8399, longitude: 77.6770 },
  { id: "INT-07", name: "Whitefield Main Road",     latitude: 12.9698, longitude: 77.7499 },
  { id: "INT-08", name: "Jayanagar 4th Block",      latitude: 12.9250, longitude: 77.5938 },
];

const LEVEL_COLORS = {
  low:      "#00ff88",
  medium:   "#f59e0b",
  high:     "#f97316",
  critical: "#ef4444",
};

function getDensityColor(density) {
  if (!density || density <= 30) return LEVEL_COLORS.low;
  if (density <= 60) return LEVEL_COLORS.medium;
  if (density <= 80) return LEVEL_COLORS.high;
  return LEVEL_COLORS.critical;
}

// ── Connection status dot ─────────────────────────────────────────────────────
function WsStatus({ connected }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{
        width: 8, height: 8, borderRadius: "50%",
        background: connected ? "#00ff88" : "#ef4444",
        boxShadow: connected ? "0 0 8px #00ff88" : "0 0 8px #ef4444",
        animation: connected ? "pulse 2s ease-in-out infinite" : "blink 0.8s step-end infinite",
      }} />
      <span style={{
        color: connected ? "#00ff88" : "#ef4444",
        fontSize: 11, fontWeight: 700,
        fontFamily: "JetBrains Mono, monospace",
        letterSpacing: 1,
      }}>
        {connected ? "LIVE" : "RECONNECTING"}
      </span>
    </div>
  );
}

// ── Upload Video Button ───────────────────────────────────────────────────────
function UploadVideoButton() {
  const [status, setStatus] = useState("idle");
  const [filename, setFilename] = useState("");
  const [message, setMessage] = useState("");
  const [progress, setProgress] = useState(0);
  const fileRef = React.useRef(null);
  const pollRef = React.useRef(null);

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Only accept video files
    if (!file.type.startsWith("video/")) {
      setMessage("Please select a video file (.mp4, .avi, .mov)");
      return;
    }

    setFilename(file.name);
    setStatus("uploading");
    setMessage(`Uploading ${file.name}...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
      await axios.post(
        apiUrl("/api/traffic/video/upload"),
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (e) => {
            const pct = Math.round((e.loaded / e.total) * 100);
            setProgress(pct);
          }
        }
      );

      setStatus("processing");
      setMessage(`Processing ${file.name} with YOLOv8...`);
      startPolling();

    } catch (err) {
      setStatus("error");
      setMessage(err.response?.data?.error || "Upload failed");
    }

    // Reset file input
    if (fileRef.current) fileRef.current.value = "";
  };

  const startPolling = () => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await axios.get(
          apiUrl("/api/traffic/video/status")
        );
        const data = res.data;
        setMessage(data.message);

        if (!data.running) {
          clearInterval(pollRef.current);
          setStatus("done");
          setMessage("Done! Check the detection feed.");
          setTimeout(() => setStatus("idle"), 5000);
        }
      } catch (err) {
        clearInterval(pollRef.current);
        setStatus("idle");
      }
    }, 2000);
  };

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const statusColors = {
    idle:       { bg: "#1e2d40", border: "#3b82f6", color: "#3b82f6" },
    uploading:  { bg: "#1a2a1a", border: "#00ff88", color: "#00ff88" },
    processing: { bg: "#1a1a2a", border: "#f59e0b", color: "#f59e0b" },
    done:       { bg: "#1a2a1a", border: "#00ff88", color: "#00ff88" },
    error:      { bg: "#2a1a1a", border: "#ef4444", color: "#ef4444" }
  };

  const statusIcons = {
    idle:       "📹",
    uploading:  "⬆️",
    processing: "⚙️",
    done:       "✅",
    error:      "❌"
  };

  const s = statusColors[status];

  return (
    <div style={{ padding: "8px 0" }}>
      <input
        ref={fileRef}
        type="file"
        accept="video/*"
        onChange={handleFileSelect}
        style={{ display: "none" }}
      />

      <button
        onClick={() => {
          if (status === "idle" || status === "done" || status === "error") {
            fileRef.current?.click();
          }
        }}
        disabled={status === "uploading" || status === "processing"}
        style={{
          width: "100%",
          padding: "10px 16px",
          background: s.bg,
          border: `1px solid ${s.border}`,
          borderRadius: "8px",
          color: s.color,
          fontSize: "13px",
          cursor: status === "uploading" || status === "processing"
            ? "not-allowed" : "pointer",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          transition: "all 0.2s"
        }}
      >
        <span style={{ fontSize: "16px" }}>
          {statusIcons[status]}
        </span>
        <span>
          {status === "idle"       && "Upload Video"}
          {status === "uploading"  && `Uploading... ${progress}%`}
          {status === "processing" && "Running YOLOv8..."}
          {status === "done"       && "Done!"}
          {status === "error"      && "Try Again"}
        </span>
      </button>

      {/* Status message */}
      {message && status !== "idle" && (
        <div style={{
          marginTop: "6px",
          padding: "6px 10px",
          background: "#080c14",
          borderRadius: "6px",
          fontSize: "11px",
          color: s.color,
          border: `1px solid ${s.border}22`
        }}>
          {status === "processing" && (
            <div style={{
              width: "100%",
              height: "2px",
              background: "#1e2d40",
              borderRadius: "1px",
              marginBottom: "4px",
              overflow: "hidden"
            }}>
              <div style={{
                height: "100%",
                width: "40%",
                background: "#f59e0b",
                borderRadius: "1px",
                animation: "slide 1.5s infinite"
              }}/>
            </div>
          )}
          {message}
          {filename && (
            <div style={{ color: "#475569", marginTop: "2px" }}>
              File: {filename}
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes slide {
          0%   { transform: translateX(-100%) }
          100% { transform: translateX(350%) }
        }
      `}</style>
    </div>
  );
}


// ── Tab selector ──────────────────────────────────────────────────────────────
function Tab({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "8px 20px",
        borderRadius: 8,
        border: active ? "1px solid rgba(0,255,136,0.35)" : "1px solid transparent",
        background: active ? "rgba(0,255,136,0.08)" : "transparent",
        color: active ? "#00ff88" : "#94a3b8",
        fontSize: 13, fontWeight: 600, cursor: "pointer",
        fontFamily: "Space Grotesk, sans-serif",
        transition: "all 0.2s ease",
        letterSpacing: 0.5,
      }}
    >
      {label}
    </button>
  );
}

// ── Intersection sidebar item ──────────────────────────────────────────────────
function IntersectionItem({ inter, selected, onClick, liveData }) {
  const density = liveData
    ? (liveData.lane_a_density + liveData.lane_b_density) / 2
    : 0;
  const color = getDensityColor(density);

  return (
    <button
      onClick={() => onClick(inter)}
      style={{
        width: "100%", textAlign: "left",
        padding: "10px 14px", borderRadius: 10,
        border: selected ? `1px solid ${color}50` : "1px solid transparent",
        background: selected ? `${color}08` : "transparent",
        cursor: "pointer", transition: "all 0.2s ease",
        display: "flex", alignItems: "center", gap: 10,
      }}
    >
      <div style={{
        width: 8, height: 8, borderRadius: "50%",
        background: color, flexShrink: 0,
        boxShadow: `0 0 6px ${color}`,
      }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{
          color: "#475569", fontSize: 10, margin: 0,
          fontFamily: "JetBrains Mono, monospace", fontWeight: 700,
        }}>{inter.id}</p>
        <p style={{
          color: selected ? "#f1f5f9" : "#94a3b8",
          fontSize: 12, margin: "1px 0 0",
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          fontFamily: "Space Grotesk, sans-serif",
        }}>{inter.name}</p>
      </div>
      {density > 0 && (
        <span style={{
          color, fontSize: 10, fontFamily: "JetBrains Mono, monospace",
          fontWeight: 700, flexShrink: 0,
        }}>{density.toFixed(0)}%</span>
      )}
    </button>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const { densityData, signalData, emergencyData, isEmergency, densityHistory, isConnected, allIntersectionData } = useWebSocket();
  const [intersections, setIntersections] = useState(DEFAULT_INTERSECTIONS);
  const [selectedIntersection, setSelectedIntersection] = useState(DEFAULT_INTERSECTIONS[0]);
  const [activeTab, setActiveTab] = useState("overview");
  const [simulating, setSimulating] = useState(false);

  useEffect(() => {
    fetchIntersections()
      .then(res => {
        const list = res.data ?? [];
        if (list.length > 0) {
          setIntersections(list);
          setSelectedIntersection(list[0]);
        }
      })
      .catch(() => {});
  }, []);

  const handleSimulate = async () => {
    setSimulating(true);
    try { await simulateEmergency(); } catch (e) { console.error(e); }
    finally { setSimulating(false); }
  };

  // Get live data for the selected intersection
  const selectedData = allIntersectionData?.[selectedIntersection?.id] || densityData || {};
  const totalVehicles = Object.values(allIntersectionData || {})
    .reduce((s, d) => s + (d?.lane_a_count || 0) + (d?.lane_b_count || 0), 0);

  // Emergency route intersections
  const emergencyRoute = ["INT-01", "INT-02", "INT-03", "INT-04"];

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#080c14", color: "#f1f5f9", overflow: "hidden" }}>

      {/* ── Top navbar ───────────────────────────────────────────────────────── */}
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px", height: 56,
        background: "rgba(8,12,20,0.98)",
        borderBottom: "1px solid #1e2d40",
        backdropFilter: "blur(10px)",
        flexShrink: 0,
        zIndex: 100,
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "rgba(0,255,136,0.1)",
            border: "1px solid rgba(0,255,136,0.25)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18,
          }}>🚦</div>
          <div>
            <p style={{ fontFamily: "Space Grotesk, sans-serif", fontWeight: 700, fontSize: 15, margin: 0, lineHeight: 1 }}>
              SmartTraffic<span style={{ color: "#00ff88" }}> AI</span>
            </p>
            <p style={{ color: "#475569", fontSize: 10, margin: "2px 0 0", fontFamily: "JetBrains Mono, monospace" }}>
              Adaptive Signal Management
            </p>
          </div>
        </div>

        {/* Center tabs */}
        <div style={{ display: "flex", gap: 4 }}>
          <Tab label="Overview"  active={activeTab === "overview"}  onClick={() => setActiveTab("overview")}  />
          <Tab label="Map"       active={activeTab === "map"}       onClick={() => setActiveTab("map")}       />
          <Tab label="Analytics" active={activeTab === "analytics"} onClick={() => setActiveTab("analytics")} />
        </div>

        {/* Right controls */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <WsStatus connected={isConnected} />
          <button
            onClick={handleSimulate}
            disabled={simulating || !!emergencyData}
            style={{
              padding: "7px 16px", borderRadius: 8,
              background: emergencyData ? "rgba(239,68,68,0.08)" : "rgba(239,68,68,0.12)",
              border: "1px solid rgba(239,68,68,0.35)",
              color: emergencyData ? "#ff6666" : "#ef4444",
              fontFamily: "Space Grotesk, sans-serif", fontWeight: 600, fontSize: 12,
              cursor: (simulating || emergencyData) ? "not-allowed" : "pointer",
              opacity: simulating ? 0.7 : 1,
              transition: "all 0.2s ease",
            }}
          >
            {simulating ? "🔄 Dispatching…" : emergencyData ? "🚨 Emergency Active" : "🚨 Simulate Emergency"}
          </button>
        </div>
      </header>

      {/* ── Emergency banner ───────────────────────────────────────────────────── */}
      {emergencyData && <EmergencyAlert event={emergencyData} />}

      {/* ── Body ─────────────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* ── LEFT SIDEBAR (250px) ──────────────────────────────────────────── */}
        <aside style={{
          width: 250, flexShrink: 0,
          display: "flex", flexDirection: "column",
          background: "rgba(8,12,20,0.9)",
          borderRight: "1px solid #1e2d40",
          overflow: "hidden",
        }}>
          {/* Intersections list */}
          <div style={{ flex: 1, overflowY: "auto", padding: "12px 10px 0" }}>
            <p style={{
              color: "#475569", fontSize: 10, textTransform: "uppercase",
              letterSpacing: 1.5, margin: "0 4px 10px",
              fontFamily: "Space Grotesk, sans-serif",
            }}>
              Intersections
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {intersections.map(inter => (
                <IntersectionItem
                  key={inter.id}
                  inter={inter}
                  selected={selectedIntersection?.id === inter.id}
                  onClick={setSelectedIntersection}
                  liveData={allIntersectionData?.[inter.id]}
                />
              ))}
            </div>
          </div>

          {/* Bottom stats */}
          <div style={{
            padding: "12px 10px",
            borderTop: "1px solid #1e2d40",
            display: "flex", flexDirection: "column", gap: 8,
          }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                { icon: "🚦", label: "Intersections", val: intersections.length },
                { icon: "🚨", label: "Emergency", val: emergencyData ? "1" : "0", color: emergencyData ? "#ef4444" : "#94a3b8" },
                { icon: "🚗", label: "Total Vehicles", val: totalVehicles || "—" },
                { icon: "🔌", label: "WS Clients", val: isConnected ? "✓" : "✗", color: isConnected ? "#00ff88" : "#ef4444" },
              ].map(({ icon, label, val, color }) => (
                <div key={label} style={{
                  display: "flex", alignItems: "center", gap: 10,
                  background: "#111827", borderRadius: 8,
                  border: "1px solid #1e2d40",
                  padding: "8px 12px",
                }}>
                  <div style={{ fontSize: 16 }}>{icon}</div>
                  <div style={{ flex: 1, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <p style={{ color: "#94a3b8", fontSize: 11, margin: 0, fontFamily: "Space Grotesk, sans-serif" }}>{label}</p>
                    <p style={{
                      color: color || "#f1f5f9", fontSize: 13, fontWeight: 700,
                      margin: 0, fontFamily: "JetBrains Mono, monospace",
                    }}>{val}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Upload video button */}
            <UploadVideoButton />
          </div>
        </aside>

        {/* ── CENTER PANEL ─────────────────────────────────────────────────── */}
        <main style={{ flex: 1, overflowY: "auto", padding: 20, minWidth: 0 }}>

          {/* Intersection header (overview / analytics only) */}
          {activeTab !== "map" && selectedIntersection && (
            <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{
                background: "rgba(59,130,246,0.08)",
                border: "1px solid rgba(59,130,246,0.2)",
                borderRadius: 8,
                padding: "6px 14px",
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 13, color: "#3b82f6", fontWeight: 700,
              }}>{selectedIntersection.id}</div>
              <h2 style={{ margin: 0, fontSize: 18, fontFamily: "Space Grotesk, sans-serif", fontWeight: 700 }}>
                {selectedIntersection.name}
              </h2>
            </div>
          )}

          {/* OVERVIEW TAB */}
          {activeTab === "overview" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Dashboard
                densityData={selectedData}
                signalData={signalData}
                densityHistory={densityHistory}
                isEmergency={isEmergency}
              />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <VehicleBreakdown
                  laneAData={{
                    cars:   selectedData?.lane_a_cars   || 0,
                    bikes:  selectedData?.lane_a_bikes  || 0,
                    buses:  selectedData?.lane_a_buses  || 0,
                    trucks: selectedData?.lane_a_trucks || 0,
                  }}
                  laneBData={{
                    cars:   selectedData?.lane_b_cars   || 0,
                    bikes:  selectedData?.lane_b_bikes  || 0,
                    buses:  selectedData?.lane_b_buses  || 0,
                    trucks: selectedData?.lane_b_trucks || 0,
                  }}
                />
                <QueueInfo densityData={selectedData} />
              </div>

              {/* YOLOv8 Detection Feed — full width */}
              <ModelFeed />

              {/* Optimizer reason */}
              {signalData?.reason && (
                <div style={{
                  background: "#111827",
                  border: "1px solid #1e2d40",
                  borderRadius: 12,
                  padding: "14px 20px",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}>
                  <span style={{ fontSize: 20 }}>🤖</span>
                  <div>
                    <p style={{ color: "#475569", fontSize: 10, textTransform: "uppercase", letterSpacing: 1, margin: "0 0 4px", fontFamily: "Space Grotesk, sans-serif" }}>
                      Optimizer Decision
                    </p>
                    <p style={{ color: "#f1f5f9", fontSize: 13, margin: 0, fontFamily: "Space Grotesk, sans-serif" }}>
                      {signalData.reason}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* MAP TAB */}
          {activeTab === "map" && (
            <div style={{ height: "calc(100vh - 160px)", borderRadius: 12, overflow: "hidden" }}>
              <CityMap
                intersectionData={allIntersectionData || {}}
                isEmergency={isEmergency}
                emergencyRoute={emergencyRoute}
                onIntersectionSelect={inter => {
                  setSelectedIntersection(inter);
                }}
              />
            </div>
          )}

          {/* ANALYTICS TAB */}
          {activeTab === "analytics" && <Analytics />}
        </main>

        {/* ── RIGHT PANEL (300px) ──────────────────────────────────────────── */}
        <aside style={{
          width: 300, flexShrink: 0,
          display: "flex", flexDirection: "column", gap: 12,
          padding: 12,
          background: "rgba(8,12,20,0.9)",
          borderLeft: "1px solid #1e2d40",
          overflowY: "auto",
        }}>
          {/* Density gauges */}
          <DensityGauges densityData={selectedData} />

          {/* Live feed */}
          <LiveFeed
            intersectionId={selectedIntersection?.id || "INT-01"}
            intersectionName={selectedIntersection?.name || "MG Road"}
            densityData={selectedData}
          />
        </aside>
      </div>

      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.6;transform:scale(1.1)} }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0d1525; }
        ::-webkit-scrollbar-thumb { background: #1e2d40; border-radius: 2px; }
      `}</style>
    </div>
  );
}

// ── Density gauges (right panel) ──────────────────────────────────────────────
function DensityGauges({ densityData }) {
  const aDensity = densityData?.lane_a_density || 0;
  const bDensity = densityData?.lane_b_density || 0;
  const aCount   = densityData?.lane_a_count   || 0;
  const bCount   = densityData?.lane_b_count   || 0;

  function GaugeBar({ label, density, count, color }) {
    return (
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <span style={{ color: "#94a3b8", fontSize: 11, fontFamily: "Space Grotesk, sans-serif" }}>{label}</span>
          <span style={{ color, fontFamily: "JetBrains Mono, monospace", fontSize: 14, fontWeight: 700 }}>
            {density.toFixed(0)}%
          </span>
        </div>
        <div style={{ height: 6, background: "#1e2d40", borderRadius: 3, overflow: "hidden" }}>
          <div style={{
            height: "100%", width: `${density}%`, background: color,
            borderRadius: 3, transition: "width 0.5s ease",
            boxShadow: `0 0 8px ${color}80`,
          }} />
        </div>
        <p style={{ color: "#475569", fontSize: 10, marginTop: 4, fontFamily: "JetBrains Mono, monospace" }}>
          {count} vehicles
        </p>
      </div>
    );
  }

  return (
    <div style={{
      background: "#111827",
      border: "1px solid #1e2d40",
      borderRadius: 12,
      padding: 16,
    }}>
      <p style={{
        color: "#475569", fontSize: 10, textTransform: "uppercase",
        letterSpacing: 1.5, margin: "0 0 14px",
        fontFamily: "Space Grotesk, sans-serif",
      }}>Lane Density</p>
      <GaugeBar label="Lane A" density={aDensity} count={aCount} color={getDensityColor(aDensity)} />
      <GaugeBar label="Lane B" density={bDensity} count={bCount} color={getDensityColor(bDensity)} />
    </div>
  );
}
