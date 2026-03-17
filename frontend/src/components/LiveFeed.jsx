import React, { useState, useEffect } from "react";

const LEVEL_COLORS = {
  low:      { bg: "rgba(0,255,136,0.1)",  border: "rgba(0,255,136,0.3)",  text: "#00ff88" },
  medium:   { bg: "rgba(245,158,11,0.1)", border: "rgba(245,158,11,0.3)", text: "#f59e0b" },
  high:     { bg: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.3)", text: "#f97316" },
  critical: { bg: "rgba(239,68,68,0.1)",  border: "rgba(239,68,68,0.3)",  text: "#ef4444" },
};

function getLevel(density) {
  if (!density || density <= 30) return "low";
  if (density <= 60) return "medium";
  if (density <= 80) return "high";
  return "critical";
}

function formatTime(date) {
  return date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function LiveFeed({ intersectionName = "MG Road & Brigade Road", densityData, intersectionId = "INT-01" }) {
  const [time, setTime] = useState(new Date());
  const [connecting, setConnecting] = useState(true);

  useEffect(() => {
    if (densityData) setConnecting(false);
  }, [densityData]);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const aDensity = densityData?.lane_a_density || 0;
  const bDensity = densityData?.lane_b_density || 0;
  const avgDensity = (aDensity + bDensity) / 2;
  const aCount = densityData?.lane_a_count || 0;
  const bCount = densityData?.lane_b_count || 0;
  const totalVehicles = aCount + bCount;
  const level = getLevel(avgDensity);
  const lc = LEVEL_COLORS[level];

  return (
    <div style={{
      background: "#111827",
      border: "1px solid #1e2d40",
      borderRadius: 12,
      overflow: "hidden",
      position: "relative",
    }}>
      {/* Camera header */}
      <div style={{
        background: "#080c14",
        padding: "10px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: "1px solid #1e2d40",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 18 }}>📷</span>
          <div>
            <p style={{ color: "#f1f5f9", fontSize: 13, fontWeight: 600, margin: 0, fontFamily: "Space Grotesk, sans-serif" }}>
              {intersectionId}
            </p>
            <p style={{ color: "#94a3b8", fontSize: 11, margin: 0 }}>{intersectionName}</p>
          </div>
        </div>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          background: "rgba(239,68,68,0.1)",
          border: "1px solid rgba(239,68,68,0.3)",
          borderRadius: 6,
          padding: "4px 10px",
        }}>
          <div style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#ef4444",
            animation: "pulse 1s ease-in-out infinite",
          }} />
          <span style={{ color: "#ef4444", fontSize: 11, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>LIVE</span>
        </div>
      </div>

      {/* Camera feed area */}
      <div style={{
        position: "relative",
        background: "#080c14",
        aspectRatio: "16/9",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}>
        {connecting ? (
          <div style={{ textAlign: "center" }}>
            <div style={{
              width: 40,
              height: 40,
              border: "3px solid #1e2d40",
              borderTop: "3px solid #3b82f6",
              borderRadius: "50%",
              margin: "0 auto 12px",
              animation: "spin 1s linear infinite",
            }} />
            <p style={{ color: "#475569", fontSize: 12, fontFamily: "Space Grotesk, sans-serif" }}>Connecting to camera…</p>
          </div>
        ) : (
          <>
            {/* Simulated camera view with grid lines */}
            <div style={{ position: "absolute", inset: 0, opacity: 0.05 }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} style={{ position: "absolute", left: `${(i + 1) * 12.5}%`, top: 0, bottom: 0, width: 1, background: "#3b82f6" }} />
              ))}
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} style={{ position: "absolute", top: `${(i + 1) * 16.7}%`, left: 0, right: 0, height: 1, background: "#3b82f6" }} />
              ))}
            </div>

            {/* Lane divider */}
            <div style={{
              position: "absolute",
              left: "50%",
              top: 0,
              bottom: 0,
              width: 2,
              background: "rgba(255,255,255,0.15)",
              borderStyle: "dashed",
            }} />

            {/* Lane A label */}
            <div style={{
              position: "absolute",
              top: 12,
              left: 12,
              background: "rgba(59,130,246,0.2)",
              border: "1px solid rgba(59,130,246,0.4)",
              borderRadius: 6,
              padding: "4px 10px",
              fontSize: 11,
              color: "#3b82f6",
              fontFamily: "JetBrains Mono, monospace",
              fontWeight: 600,
            }}>
              LANE A · {aCount} veh
            </div>

            {/* Lane B label */}
            <div style={{
              position: "absolute",
              top: 12,
              right: 12,
              background: "rgba(0,255,136,0.1)",
              border: "1px solid rgba(0,255,136,0.3)",
              borderRadius: 6,
              padding: "4px 10px",
              fontSize: 11,
              color: "#00ff88",
              fontFamily: "JetBrains Mono, monospace",
              fontWeight: 600,
            }}>
              LANE B · {bCount} veh
            </div>

            {/* Vehicle dots animation */}
            <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
              {Array.from({ length: Math.min(totalVehicles, 20) }).map((_, i) => (
                <div
                  key={i}
                  style={{
                    position: "absolute",
                    width: 8,
                    height: 4,
                    borderRadius: 2,
                    background: i % 3 === 0 ? "#3b82f6" : i % 3 === 1 ? "#00ff88" : "#f59e0b",
                    left: `${(i < 10 ? 5 + (i % 10) * 9 : 55 + (i % 10) * 4)}%`,
                    top: `${20 + (i % 5) * 15}%`,
                    opacity: 0.7,
                  }}
                />
              ))}
            </div>

            {/* Density overlay */}
            <div style={{
              position: "absolute",
              bottom: 12,
              left: "50%",
              transform: "translateX(-50%)",
              background: lc.bg,
              border: `1px solid ${lc.border}`,
              borderRadius: 6,
              padding: "4px 14px",
              fontSize: 12,
              color: lc.text,
              fontWeight: 700,
              fontFamily: "Space Grotesk, sans-serif",
              textTransform: "uppercase",
              letterSpacing: 1,
            }}>
              {level} · {avgDensity.toFixed(0)}% density
            </div>
          </>
        )}
      </div>

      {/* Stats bar */}
      <div style={{
        padding: "10px 16px",
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 8,
        borderTop: "1px solid #1e2d40",
      }}>
        {[
          { label: "Total Vehicles", val: totalVehicles },
          { label: "Avg Density", val: `${avgDensity.toFixed(0)}%` },
          { label: "Updated", val: formatTime(time) },
        ].map(({ label, val }) => (
          <div key={label} style={{ textAlign: "center" }}>
            <p style={{ color: "#f1f5f9", fontSize: 13, fontWeight: 600, margin: 0, fontFamily: "JetBrains Mono, monospace" }}>{val}</p>
            <p style={{ color: "#475569", fontSize: 10, margin: "2px 0 0", fontFamily: "Space Grotesk, sans-serif" }}>{label}</p>
          </div>
        ))}
      </div>

      <style>{`
        @keyframes spin { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
      `}</style>
    </div>
  );
}
