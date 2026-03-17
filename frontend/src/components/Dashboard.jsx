import React, { useEffect, useRef, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import SignalStatus from "./SignalStatus";

// ── Helpers ───────────────────────────────────────────────────────────────────
const LEVEL_META = {
  low:      { label: "LOW",      color: "#00ff88", bg: "rgba(0,255,136,0.08)" },
  medium:   { label: "MEDIUM",   color: "#ffaa00", bg: "rgba(255,170,0,0.08)" },
  high:     { label: "HIGH",     color: "#ff6600", bg: "rgba(255,102,0,0.08)" },
  critical: { label: "CRITICAL", color: "#ff4444", bg: "rgba(255,68,68,0.08)"  },
};

function DensityGauge({ label, count, density, level }) {
  const meta = LEVEL_META[level] || LEVEL_META.low;
  const pct  = Math.min(Math.max(density ?? 0, 0), 100);

  return (
    <div style={{
      background: meta.bg,
      border: `1px solid ${meta.color}40`,
      borderRadius: 12,
      padding: 16,
      display: "flex",
      flexDirection: "column",
      gap: 10,
    }}>
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <p style={{
          fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em",
          color: "#6b7280", margin: 0, fontFamily: "Space Grotesk, sans-serif",
        }}>{label}</p>
        <span style={{
          fontSize: 10, fontWeight: 700,
          padding: "2px 8px", borderRadius: 999,
          background: `${meta.color}22`, color: meta.color,
          fontFamily: "JetBrains Mono, monospace",
        }}>
          {meta.label}
        </span>
      </div>

      {/* Big count */}
      <p style={{
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 48, fontWeight: 700, lineHeight: 1,
        color: meta.color, margin: 0,
      }}>
        {count ?? 0}
        <span style={{ fontSize: 14, color: "#6b7280", marginLeft: 4 }}>veh</span>
      </p>

      {/* Progress bar */}
      <div style={{ width: "100%", height: 8, borderRadius: 4, background: "#1e2d40", overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${pct}%`,
          background: meta.color, borderRadius: 4,
          transition: "width 0.7s ease",
          boxShadow: `0 0 10px ${meta.color}80`,
        }} />
      </div>
      <p style={{
        textAlign: "right", fontFamily: "JetBrains Mono, monospace",
        fontSize: 12, color: meta.color, margin: 0,
      }}>
        {pct.toFixed(1)}%
      </p>
    </div>
  );
}

function OptimizationBox({ signalData }) {
  if (!signalData) {
    return (
      <div style={{
        background: "#111827", border: "1px solid #1e2d40",
        borderRadius: 12, padding: 16,
      }}>
        <p style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "#4b5563", marginBottom: 8, fontFamily: "Space Grotesk, sans-serif" }}>
          Optimizer
        </p>
        <p style={{ color: "#4b5563", fontSize: 13, fontFamily: "Space Grotesk, sans-serif" }}>Awaiting first signal update…</p>
      </div>
    );
  }

  return (
    <div style={{
      background: "#111827", border: "1px solid #1e2d40",
      borderRadius: 12, padding: 16,
      display: "flex", flexDirection: "column", gap: 8,
    }}>
      <p style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "#6b7280", margin: 0, fontFamily: "Space Grotesk, sans-serif" }}>
        Optimizer
      </p>
      <p style={{ fontSize: 13, color: "#d1d5db", lineHeight: 1.6, margin: 0, fontFamily: "Space Grotesk, sans-serif" }}>
        {signalData.optimization_reason || "Normal adaptive mode."}
      </p>
      <div style={{ display: "flex", gap: 16, marginTop: 4, fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: "#6b7280" }}>
        <span>Cycle: <span style={{ color: "#f59e0b" }}>{signalData.cycle_time ?? "–"}s</span></span>
        <span>Updated: <span style={{ color: "#9ca3af" }}>
          {signalData.created_at
            ? new Date(signalData.created_at).toLocaleTimeString()
            : "–"}
        </span></span>
        {signalData.is_emergency_override && (
          <span style={{ color: "#f87171", fontWeight: 700 }}>⚡ EMERGENCY OVERRIDE</span>
        )}
      </div>
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#0d1526", border: "1px solid #1f2d44",
      borderRadius: 8, padding: "8px 12px",
      fontSize: 11, fontFamily: "JetBrains Mono, monospace",
    }}>
      <p style={{ color: "#9ca3af", marginBottom: 4 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color, margin: 0 }}>
          {p.name}: {p.value?.toFixed(1)}%
        </p>
      ))}
    </div>
  );
};

// ── Main Dashboard ─────────────────────────────────────────────────────────────
export default function Dashboard({ densityData, signalData, densityHistory, isEmergency = false }) {
  const [aRemaining, setARemaining] = useState(0);
  const [bRemaining, setBRemaining] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    if (signalData) {
      if (signalData.is_emergency || isEmergency) {
        setARemaining(signalData.lane_a_green_seconds ?? 90);
        setBRemaining(signalData.lane_b_green_seconds ?? 90);
      } else {
        setARemaining(Math.round(signalData.lane_a_green_seconds ?? 30));
        setBRemaining(Math.round(signalData.lane_b_green_seconds ?? 30));
      }
    }
  }, [signalData, isEmergency]);

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setARemaining((p) => Math.max(0, p - 1));
      setBRemaining((p) => Math.max(0, p - 1));
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  const laneA = densityData ?? {};

  const aGreen = isEmergency || aRemaining > 0;
  const phaseA = isEmergency ? "green" : (aGreen ? "green" : "red");
  const phaseB = isEmergency ? "green" : (aGreen ? "red" : "green");

  // Timing pill colors
  const timingRows = [
    { label: "A Green", val: signalData?.lane_a_green_seconds, color: "#00ff88", border: "#00ff88" },
    { label: "A Red",   val: signalData?.lane_a_red_seconds,   color: "#ff4444", border: "#ff4444" },
    { label: "B Green", val: signalData?.lane_b_green_seconds, color: "#00ff88", border: "#00ff88" },
    { label: "B Red",   val: signalData?.lane_b_red_seconds,   color: "#ff4444", border: "#ff4444" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, width: "100%" }}>

      {/* ── Row 1: Signal lights + Density gauges ─────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

        {/* Signal phases card */}
        <div style={{
          background: "#111827",
          border: "1px solid #1e2d40",
          borderRadius: 12,
          padding: 20,
        }}>
          <p style={{
            fontSize: 10, textTransform: "uppercase", letterSpacing: "0.15em",
            color: "#475569", marginBottom: 20,
            fontFamily: "Space Grotesk, sans-serif",
          }}>Signal Phases</p>

          {/* Traffic lights side by side */}
          <div style={{
            display: "flex",
            justifyContent: "space-around",
            alignItems: "center",
          }}>
            <SignalStatus
              laneName="Lane A"
              phase={phaseA}
              secondsRemaining={aRemaining}
              isEmergency={isEmergency}
            />
            <div style={{ width: 1, alignSelf: "stretch", background: "#1e2d40" }} />
            <SignalStatus
              laneName="Lane B"
              phase={phaseB}
              secondsRemaining={bRemaining}
              isEmergency={isEmergency}
            />
          </div>

          {/* Timing pills */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 20 }}>
            {timingRows.map(({ label, val, color, border }) => (
              <div
                key={label}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  background: `${color}10`,
                  border: `1px solid ${border}40`,
                  borderRadius: 6,
                  padding: "6px 12px",
                }}
              >
                <span style={{
                  fontSize: 11, color: "#94a3b8",
                  fontFamily: "Space Grotesk, sans-serif",
                }}>{label}</span>
                <span style={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 13, fontWeight: 700,
                  color,
                }}>
                  {val != null ? `${val}s` : "–"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Lane Density card */}
        <div style={{
          background: "#111827",
          border: "1px solid #1e2d40",
          borderRadius: 12,
          padding: 20,
        }}>
          <p style={{
            fontSize: 10, textTransform: "uppercase", letterSpacing: "0.15em",
            color: "#475569", marginBottom: 16,
            fontFamily: "Space Grotesk, sans-serif",
          }}>Lane Density</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <DensityGauge
              label="Lane A"
              count={laneA.lane_a_count}
              density={laneA.lane_a_density}
              level={laneA.lane_a_level ?? "low"}
            />
            <DensityGauge
              label="Lane B"
              count={laneA.lane_b_count}
              density={laneA.lane_b_density}
              level={laneA.lane_b_level ?? "low"}
            />
          </div>
        </div>
      </div>

      {/* ── Row 2: Real-time chart ──────────────────────────────────────────── */}
      <div style={{
        background: "#111827",
        border: "1px solid #1e2d40",
        borderRadius: 12,
        padding: 20,
      }}>
        <p style={{
          fontSize: 10, textTransform: "uppercase", letterSpacing: "0.15em",
          color: "#475569", marginBottom: 16,
          fontFamily: "Space Grotesk, sans-serif",
        }}>
          Real-time Density — last 60s
        </p>

        {densityHistory.length === 0 ? (
          <div style={{ height: 208, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <p style={{ color: "#4b5563", fontSize: 13, fontFamily: "Space Grotesk, sans-serif" }}>Waiting for data…</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={densityHistory} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a2744" />
              <XAxis
                dataKey="time"
                tick={{ fill: "#4b5563", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
                tick={{ fill: "#4b5563", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: 11, color: "#9ca3af", fontFamily: "monospace" }}
              />
              <Line
                type="monotoneX"
                dataKey="laneA"
                name="Lane A"
                stroke="#60a5fa"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotoneX"
                dataKey="laneB"
                name="Lane B"
                stroke="#00ff88"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Row 3: Optimization info ────────────────────────────────────────── */}
      <OptimizationBox signalData={signalData} />
    </div>
  );
}
