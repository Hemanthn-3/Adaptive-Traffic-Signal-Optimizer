import React from "react";

const FLASH_STYLE = `
  @keyframes flash {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
  }
`;

/**
 * SVG traffic light component.
 * phase:        "green" | "yellow" | "red"
 * isEmergency:  boolean — when true forces both lights GREEN with flash + OVERRIDE badge
 */
export default function SignalStatus({ laneName, phase = "red", secondsRemaining = 0, isEmergency = false }) {
  const effectivePhase = isEmergency ? "green" : phase;

  const isRed    = effectivePhase === "red";
  const isYellow = effectivePhase === "yellow";
  const isGreen  = effectivePhase === "green";

  const redColor    = isRed    ? "#ff3b3b" : "#3d0e0e";
  const yellowColor = isYellow ? "#ffc107" : "#3d2e00";
  const greenColor  = isGreen  ? "#00ff88" : "#003d20";

  const glowRed    = isRed    ? "drop-shadow(0 0 10px #ff3b3b)" : "none";
  const glowYellow = isYellow ? "drop-shadow(0 0 10px #ffc107)" : "none";
  const glowGreen  = isGreen  ? "drop-shadow(0 0 10px #00ff88)" : "none";

  const flashStyle = isEmergency
    ? { animation: "flash 0.8s infinite" }
    : {};

  const phaseColor = isGreen ? "#00ff88" : isYellow ? "#ffc107" : "#ff4444";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
      <style>{FLASH_STYLE}</style>

      {/* Traffic light housing */}
      <svg width="72" height="180" viewBox="0 0 72 180" style={{ filter: "drop-shadow(0 8px 16px rgba(0,0,0,0.8))" }}>
        {/* Housing */}
        <rect x="4" y="4" width="64" height="172" rx="10" fill="#111827" stroke="#1f2937" strokeWidth="2" />

        {/* Red */}
        <circle
          cx="36" cy="40" r="22"
          fill={redColor}
          style={{ filter: glowRed, transition: "filter 0.4s, fill 0.4s" }}
        />
        {/* Yellow */}
        <circle
          cx="36" cy="90" r="22"
          fill={yellowColor}
          style={{ filter: glowYellow, transition: "filter 0.4s, fill 0.4s" }}
        />
        {/* Green */}
        <circle
          cx="36" cy="140" r="22"
          fill={greenColor}
          style={{ filter: glowGreen, transition: "filter 0.4s, fill 0.4s", ...flashStyle }}
        />
      </svg>

      {/* Label */}
      <div style={{ textAlign: "center" }}>
        <p style={{
          fontSize: 13, color: "#9ca3af", fontWeight: 500,
          margin: 0, fontFamily: "Space Grotesk, sans-serif",
        }}>{laneName}</p>
        <p style={{
          fontSize: 24, fontFamily: "JetBrains Mono, monospace",
          fontWeight: 700, color: phaseColor,
          margin: "2px 0 0",
        }}>
          {secondsRemaining}
          <span style={{ fontSize: 13, marginLeft: 4, color: "#6b7280" }}>s</span>
        </p>
        <p style={{
          fontSize: 10, textTransform: "uppercase",
          letterSpacing: "0.15em", marginTop: 4,
          color: phaseColor, fontFamily: "JetBrains Mono, monospace",
        }}>
          {effectivePhase}
        </p>

        {/* OVERRIDE badge */}
        {isEmergency && (
          <span style={{
            display: "inline-block",
            marginTop: 6,
            background: "#ff1a1a",
            color: "#fff",
            fontSize: 10,
            fontWeight: "bold",
            letterSpacing: "0.1em",
            padding: "2px 8px",
            borderRadius: 4,
            animation: "flash 0.8s infinite",
          }}>
            OVERRIDE
          </span>
        )}
      </div>
    </div>
  );
}
