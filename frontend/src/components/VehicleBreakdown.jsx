import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LabelList
} from "recharts";

const TYPES = ["Car", "Bike", "Bus", "Truck"];

function getValue(data, key, fallback = 0) {
  return typeof data?.[key] === "number" ? data[key] : fallback;
}

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
          <span style={{ color: "#f1f5f9", fontSize: 12, fontWeight: 700 }}>{p.value}</span>
        </div>
      ))}
    </div>
  );
};

export default function VehicleBreakdown({ laneAData = {}, laneBData = {} }) {
  const data = TYPES.map(t => ({
    type: t,
    "Lane A": getValue(laneAData, t.toLowerCase() + "s") || getValue(laneAData, t.toLowerCase()),
    "Lane B": getValue(laneBData, t.toLowerCase() + "s") || getValue(laneBData, t.toLowerCase()),
  }));

  const total = data.reduce((s, d) => s + d["Lane A"] + d["Lane B"], 0);

  return (
    <div style={{
      background: "#111827",
      border: "1px solid #1e2d40",
      borderRadius: 12,
      padding: "20px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h3 style={{ color: "#f1f5f9", fontSize: 14, fontWeight: 600, margin: 0, fontFamily: "Space Grotesk, sans-serif" }}>
            Vehicle Breakdown
          </h3>
          <p style={{ color: "#475569", fontSize: 11, margin: "4px 0 0", fontFamily: "Space Grotesk, sans-serif" }}>
            Count by type per lane
          </p>
        </div>
        <div style={{
          background: "rgba(59,130,246,0.1)",
          border: "1px solid rgba(59,130,246,0.3)",
          borderRadius: 8,
          padding: "4px 12px",
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 14,
          color: "#3b82f6",
          fontWeight: 700,
        }}>
          {total} total
        </div>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} barGap={4} barCategoryGap="25%">
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2d40" vertical={false} />
          <XAxis
            dataKey="type"
            tick={{ fill: "#94a3b8", fontSize: 12, fontFamily: "Space Grotesk, sans-serif" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#475569", fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Legend
            wrapperStyle={{ fontFamily: "Space Grotesk, sans-serif", fontSize: 12, color: "#94a3b8", paddingTop: 12 }}
          />
          <Bar dataKey="Lane A" fill="#3b82f6" radius={[4, 4, 0, 0]}>
            <LabelList dataKey="Lane A" position="top" style={{ fill: "#3b82f6", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }} />
          </Bar>
          <Bar dataKey="Lane B" fill="#00ff88" radius={[4, 4, 0, 0]}>
            <LabelList dataKey="Lane B" position="top" style={{ fill: "#00ff88", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
