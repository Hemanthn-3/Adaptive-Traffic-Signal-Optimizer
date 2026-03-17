import { useState } from "react"

export default function ModelFeed() {
  const [isLive, setIsLive] = useState(false)
  const [error, setError] = useState(false)

  return (
    <div style={{
      background: "#111827",
      border: "1px solid #1e2d40",
      borderRadius: "12px",
      padding: "16px",
    }}>

      {/* ── Header ───────────────────────────────────────────────────── */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "12px",
      }}>
        <span style={{
          color: "#f1f5f9",
          fontWeight: 600,
          fontSize: "13px",
          fontFamily: "Space Grotesk, sans-serif",
          letterSpacing: 0.5,
        }}>
          YOLOv8 Detection Feed
        </span>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span style={{
            background: isLive ? "rgba(239,68,68,0.15)" : "rgba(71,85,105,0.15)",
            border: `1px solid ${isLive ? "#ef4444" : "#475569"}`,
            color: isLive ? "#ef4444" : "#475569",
            borderRadius: "20px",
            padding: "2px 10px",
            fontSize: "11px",
            fontFamily: "JetBrains Mono, monospace",
            animation: isLive ? "pulse 1.5s ease-in-out infinite" : "none",
          }}>
            ● {isLive ? "LIVE" : "LOADING"}
          </span>
          <span style={{
            background: "rgba(59,130,246,0.15)",
            border: "1px solid #3b82f6",
            color: "#3b82f6",
            borderRadius: "20px",
            padding: "2px 10px",
            fontSize: "11px",
            fontFamily: "JetBrains Mono, monospace",
          }}>
            best.pt
          </span>
        </div>
      </div>

      {/* ── Video / Fallback ──────────────────────────────────────────── */}
      {!error ? (
        <img
          src="http://localhost:8000/api/traffic/video/stream"
          alt="YOLOv8 Vehicle Detection"
          onError={() => { setError(true); setIsLive(false); }}
          onLoad={() => setIsLive(true)}
          style={{
            width: "100%",
            borderRadius: "8px",
            border: "1px solid #1e2d40",
            background: "#080c14",
            display: "block",
          }}
        />
      ) : (
        <div style={{
          width: "100%",
          height: "220px",
          background: "#080c14",
          borderRadius: "8px",
          border: "1px solid #1e2d40",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "10px",
        }}>
          <span style={{ fontSize: "36px" }}>📹</span>
          <span style={{ color: "#94a3b8", fontSize: "13px", fontFamily: "Space Grotesk, sans-serif" }}>
            Backend stream not available
          </span>
          <p style={{ color: "#475569", fontSize: "11px", margin: 0, fontFamily: "Space Grotesk, sans-serif" }}>
            Start the backend, then run:
          </p>
          <code style={{
            color: "#3b82f6",
            fontSize: "11px",
            background: "#111827",
            padding: "5px 10px",
            borderRadius: "6px",
            border: "1px solid #1e2d40",
            fontFamily: "JetBrains Mono, monospace",
          }}>
            python demo.py ml/test_videos/sample_video.mp4
          </code>
        </div>
      )}

      {/* ── Stats bar ────────────────────────────────────────────────── */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        marginTop: "10px",
        padding: "8px 14px",
        background: "#080c14",
        borderRadius: "8px",
        border: "1px solid #1e2d40",
        fontSize: "11px",
        color: "#94a3b8",
        fontFamily: "JetBrains Mono, monospace",
        flexWrap: "wrap",
        gap: "6px",
      }}>
        <span>Model: <span style={{ color: "#00ff88" }}>best.pt (fine-tuned)</span></span>
        <span>Classes: <span style={{ color: "#00ff88" }}>vehicle</span></span>
        <span>Conf: <span style={{ color: "#00ff88" }}>0.3+</span></span>
        <span>Speed: <span style={{ color: "#00ff88" }}>~30ms/frame</span></span>
      </div>
    </div>
  )
}
