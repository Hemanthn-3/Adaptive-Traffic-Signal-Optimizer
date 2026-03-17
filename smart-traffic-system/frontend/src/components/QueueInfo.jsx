import React from "react";

function QueueCard({ lane, color, queueMeters, timeToClear, flowRate, density }) {
  const maxQueue = 200;  // meters reference
  const progress = Math.min(100, (queueMeters / maxQueue) * 100);

  return (
    <div style={{
      background: "#080c14",
      border: `1px solid ${color}33`,
      borderRadius: 10,
      padding: 16,
      flex: 1,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <span style={{ color, fontSize: 12, fontWeight: 700, fontFamily: "Space Grotesk, sans-serif", textTransform: "uppercase", letterSpacing: 1 }}>
          {lane} Queue
        </span>
        <span style={{
          background: `${color}15`,
          border: `1px solid ${color}40`,
          color,
          borderRadius: 4,
          padding: "2px 8px",
          fontSize: 10,
          fontFamily: "JetBrains Mono, monospace",
          fontWeight: 600,
        }}>
          {density?.toFixed(0) || 0}%
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 8, marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16 }}>🚗</span>
          <div>
            <p style={{ color: "#f1f5f9", fontSize: 18, fontWeight: 700, margin: 0, fontFamily: "JetBrains Mono, monospace" }}>
              {queueMeters}m
            </p>
            <p style={{ color: "#475569", fontSize: 10, margin: 0 }}>Queue length</p>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16 }}>⏱</span>
          <div>
            <p style={{ color: "#f1f5f9", fontSize: 18, fontWeight: 700, margin: 0, fontFamily: "JetBrains Mono, monospace" }}>
              {timeToClear}s
            </p>
            <p style={{ color: "#475569", fontSize: 10, margin: 0 }}>Time to clear</p>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16 }}>📊</span>
          <div>
            <p style={{ color: "#f1f5f9", fontSize: 18, fontWeight: 700, margin: 0, fontFamily: "JetBrains Mono, monospace" }}>
              {flowRate} v/min
            </p>
            <p style={{ color: "#475569", fontSize: 10, margin: 0 }}>Flow rate</p>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 4, background: "#1e2d40", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%",
          width: `${progress}%`,
          background: color,
          borderRadius: 2,
          transition: "width 0.5s ease",
        }} />
      </div>
    </div>
  );
}

export default function QueueInfo({ laneA = {}, laneB = {}, densityData }) {
  const aDensity = densityData?.lane_a_density || laneA.density || 0;
  const bDensity = densityData?.lane_b_density || laneB.density || 0;
  const aCount   = densityData?.lane_a_count   || laneA.vehicle_count || 0;
  const bCount   = densityData?.lane_b_count   || laneB.vehicle_count || 0;

  const aQueue   = densityData?.lane_a_queue_meters  ?? (aCount * 6);
  const bQueue   = densityData?.lane_b_queue_meters  ?? (bCount * 6);
  const aTTC     = densityData?.lane_a_time_to_clear ?? Math.max(10, Math.min(90, aCount * 2));
  const bTTC     = densityData?.lane_b_time_to_clear ?? Math.max(10, Math.min(90, bCount * 2));
  const aFlow    = aCount > 0 ? Math.round((aCount / Math.max(1, aTTC)) * 60) : 0;
  const bFlow    = bCount > 0 ? Math.round((bCount / Math.max(1, bTTC)) * 60) : 0;

  return (
    <div style={{
      background: "#111827",
      border: "1px solid #1e2d40",
      borderRadius: 12,
      padding: 20,
    }}>
      <h3 style={{
        color: "#f1f5f9",
        fontSize: 14,
        fontWeight: 600,
        margin: "0 0 16px",
        fontFamily: "Space Grotesk, sans-serif",
      }}>
        Queue Status
      </h3>
      <div style={{ display: "flex", gap: 12 }}>
        <QueueCard
          lane="Lane A"
          color="#3b82f6"
          queueMeters={aQueue}
          timeToClear={Math.round(aTTC)}
          flowRate={aFlow}
          density={aDensity}
        />
        <QueueCard
          lane="Lane B"
          color="#00ff88"
          queueMeters={bQueue}
          timeToClear={Math.round(bTTC)}
          flowRate={bFlow}
          density={bDensity}
        />
      </div>
    </div>
  );
}
