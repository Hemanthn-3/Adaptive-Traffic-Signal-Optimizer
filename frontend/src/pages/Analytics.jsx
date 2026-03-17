import React, { useMemo } from "react";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";

// ── 24h simulated history ──────────────────────────────────────────────
function generate24HHistory() {
  const hours = [];
  for (let h = 0; h < 24; h++) {
    let base;
    if (h >= 8 && h <= 10) base = 75;
    else if (h >= 17 && h <= 19) base = 85;
    else if (h >= 12 && h <= 14) base = 50;
    else if (h >= 22 || h <= 6) base = 15;
    else base = 35;

    hours.push({
      hour: `${String(h).padStart(2, "0")}:00`,
      "Lane A": Math.min(100, base + Math.round((Math.random() - 0.5) * 15)),
      "Lane B": Math.min(100, base * 0.85 + Math.round((Math.random() - 0.5) * 15)),
    });
  }
  return hours;
}

const pieData = [
  { name: "Car",   value: 60, color: "#3b82f6" },
  { name: "Bike",  value: 25, color: "#06b6d4" },
  { name: "Bus",   value: 10, color: "#f59e0b" },
  { name: "Truck", value:  5, color: "#ef4444" },
];

const intersectionTable = [
  { id: "INT-01", name: "MG Road & Brigade Road", avg: 65, peak: 88, today: 1240, status: "high" },
  { id: "INT-02", name: "Silk Board Junction",    avg: 72, peak: 95, today: 1850, status: "critical" },
  { id: "INT-03", name: "KR Circle",              avg: 48, peak: 71, today: 980,  status: "medium" },
  { id: "INT-04", name: "Hebbal Flyover",         avg: 35, peak: 52, today: 720,  status: "low" },
  { id: "INT-05", name: "Marathahalli Bridge",    avg: 58, peak: 79, today: 1100, status: "medium" },
  { id: "INT-06", name: "Electronic City",        avg: 41, peak: 63, today: 830,  status: "medium" },
  { id: "INT-07", name: "Whitefield Main Road",   avg: 29, peak: 45, today: 590,  status: "low" },
  { id: "INT-08", name: "Jayanagar 4th Block",    avg: 53, peak: 74, today: 1020, status: "medium" },
];

const STATUS_COLORS = {
  low:      "#00ff88",
  medium:   "#f59e0b",
  high:     "#f97316",
  critical: "#ef4444",
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#111827",
      border: "1px solid #1e2d40",
      borderRadius: 8,
      padding: "10px 14px",
      fontFamily: "JetBrains Mono, monospace",
    }}>
      <p style={{ color: "#94a3b8", fontSize: 11, marginBottom: 6 }}>{label}</p>
      {payload.map(p => (
        <div key={p.name} style={{ display: "flex", justifyContent: "space-between", gap: 16, marginBottom: 2 }}>
          <span style={{ color: p.color, fontSize: 12 }}>{p.name}</span>
          <span style={{ color: "#f1f5f9", fontSize: 12, fontWeight: 700 }}>{p.value}%</span>
        </div>
      ))}
    </div>
  );
};

const PieTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div style={{ background: "#111827", border: "1px solid #1e2d40", borderRadius: 8, padding: "8px 12px", fontFamily: "Space Grotesk, sans-serif" }}>
      <span style={{ color: d.payload.color, fontWeight: 700 }}>{d.name}: </span>
      <span style={{ color: "#f1f5f9" }}>{d.value}%</span>
    </div>
  );
};

function SummaryCard({ label, value, sub, color = "#3b82f6", icon }) {
  return (
    <div style={{
      background: "#111827",
      border: "1px solid #1e2d40",
      borderRadius: 12,
      padding: "16px 20px",
      flex: 1,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <span style={{ fontSize: 22 }}>{icon}</span>
        <p style={{ color: "#475569", fontSize: 11, margin: 0, fontFamily: "Space Grotesk, sans-serif", textTransform: "uppercase", letterSpacing: 1 }}>
          {label}
        </p>
      </div>
      <p style={{ color, fontSize: 28, fontWeight: 700, margin: "0 0 4px", fontFamily: "JetBrains Mono, monospace" }}>{value}</p>
      {sub && <p style={{ color: "#475569", fontSize: 11, margin: 0, fontFamily: "Space Grotesk, sans-serif" }}>{sub}</p>}
    </div>
  );
}

export default function Analytics() {
  const history = useMemo(() => generate24HHistory(), []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Summary cards */}
      <div style={{ display: "flex", gap: 12 }}>
        <SummaryCard icon="🚗" label="Total Vehicles Today" value="8,330" sub="↑ 12% vs yesterday" color="#3b82f6" />
        <SummaryCard icon="📊" label="Avg Density" value="52%" sub="All intersections" color="#f59e0b" />
        <SummaryCard icon="⏰" label="Peak Hour" value="18:00" sub="Evening rush 85% density" color="#f97316" />
        <SummaryCard icon="🚨" label="Emergency Events" value="3" sub="Today (last: 2h ago)" color="#ef4444" />
      </div>

      {/* 24-hour density chart */}
      <div style={{
        background: "#111827",
        border: "1px solid #1e2d40",
        borderRadius: 12,
        padding: 20,
      }}>
        <h3 style={{ color: "#f1f5f9", fontSize: 14, fontWeight: 600, margin: "0 0 16px", fontFamily: "Space Grotesk, sans-serif" }}>
          24-Hour Density Trend
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={history}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d40" vertical={false} />
            <XAxis
              dataKey="hour"
              tick={{ fill: "#475569", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }}
              axisLine={false}
              tickLine={false}
              interval={3}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: "#475569", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }}
              axisLine={false}
              tickLine={false}
              unit="%"
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontFamily: "Space Grotesk, sans-serif", fontSize: 12, color: "#94a3b8", paddingTop: 12 }}
            />
            <Line type="monotone" dataKey="Lane A" stroke="#3b82f6" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="Lane B" stroke="#00ff88" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Pie chart + Performance metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Vehicle type pie */}
        <div style={{
          background: "#111827",
          border: "1px solid #1e2d40",
          borderRadius: 12,
          padding: 20,
        }}>
          <h3 style={{ color: "#f1f5f9", fontSize: 14, fontWeight: 600, margin: "0 0 16px", fontFamily: "Space Grotesk, sans-serif" }}>
            Vehicle Type Distribution
          </h3>
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3} dataKey="value">
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ flex: 1 }}>
              {pieData.map(d => (
                <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 10, height: 10, borderRadius: 2, background: d.color, flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "#94a3b8", fontSize: 12, fontFamily: "Space Grotesk, sans-serif" }}>{d.name}</span>
                      <span style={{ color: "#f1f5f9", fontSize: 12, fontFamily: "JetBrains Mono, monospace", fontWeight: 700 }}>{d.value}%</span>
                    </div>
                    <div style={{ height: 3, background: "#1e2d40", borderRadius: 2, marginTop: 4 }}>
                      <div style={{ height: "100%", width: `${d.value}%`, background: d.color, borderRadius: 2 }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Signal efficiency */}
        <div style={{
          background: "#111827",
          border: "1px solid #1e2d40",
          borderRadius: 12,
          padding: 20,
        }}>
          <h3 style={{ color: "#f1f5f9", fontSize: 14, fontWeight: 600, margin: "0 0 16px", fontFamily: "Space Grotesk, sans-serif" }}>
            Signal Efficiency Metrics
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[
              { label: "Vehicles / green second", val: "4.2", unit: "veh/s", good: true },
              { label: "Avg cycle time", val: "58", unit: "seconds", good: true },
              { label: "Green utilization", val: "73%", unit: "", good: true },
              { label: "Red wait time", val: "28", unit: "seconds", good: true },
              { label: "Emergency activations", val: "3", unit: "today", good: false },
              { label: "Uptime", val: "99.8%", unit: "", good: true },
            ].map(({ label, val, unit, good }) => (
              <div key={label} style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "8px 12px",
                background: "#080c14",
                borderRadius: 8,
                border: "1px solid #1e2d40",
              }}>
                <span style={{ color: "#94a3b8", fontSize: 12, fontFamily: "Space Grotesk, sans-serif" }}>{label}</span>
                <span style={{
                  color: good ? "#00ff88" : "#f59e0b",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 14,
                  fontWeight: 700,
                }}>
                  {val} <span style={{ color: "#475569", fontSize: 10 }}>{unit}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Intersection performance table */}
      <div style={{
        background: "#111827",
        border: "1px solid #1e2d40",
        borderRadius: 12,
        padding: 20,
      }}>
        <h3 style={{ color: "#f1f5f9", fontSize: 14, fontWeight: 600, margin: "0 0 16px", fontFamily: "Space Grotesk, sans-serif" }}>
          Intersection Performance
        </h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "Space Grotesk, sans-serif" }}>
          <thead>
            <tr>
              {["ID", "Name", "Avg Density", "Peak", "Vehicles Today", "Status"].map(h => (
                <th key={h} style={{
                  textAlign: "left",
                  padding: "8px 12px",
                  color: "#475569",
                  fontSize: 11,
                  textTransform: "uppercase",
                  letterSpacing: 1,
                  borderBottom: "1px solid #1e2d40",
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {intersectionTable.map((row, i) => (
              <tr key={row.id} style={{ background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)" }}>
                <td style={{ padding: "10px 12px", color: "#3b82f6", fontSize: 12, fontFamily: "JetBrains Mono, monospace" }}>{row.id}</td>
                <td style={{ padding: "10px 12px", color: "#f1f5f9", fontSize: 13 }}>{row.name}</td>
                <td style={{ padding: "10px 12px", color: "#94a3b8", fontSize: 12, fontFamily: "JetBrains Mono, monospace" }}>{row.avg}%</td>
                <td style={{ padding: "10px 12px", color: STATUS_COLORS[row.status] || "#94a3b8", fontSize: 12, fontFamily: "JetBrains Mono, monospace" }}>{row.peak}%</td>
                <td style={{ padding: "10px 12px", color: "#94a3b8", fontSize: 12, fontFamily: "JetBrains Mono, monospace" }}>{row.today.toLocaleString()}</td>
                <td style={{ padding: "10px 12px" }}>
                  <span style={{
                    background: `${STATUS_COLORS[row.status]}15`,
                    border: `1px solid ${STATUS_COLORS[row.status]}40`,
                    color: STATUS_COLORS[row.status],
                    borderRadius: 4,
                    padding: "2px 8px",
                    fontSize: 10,
                    fontWeight: 700,
                    textTransform: "uppercase",
                  }}>
                    {row.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
