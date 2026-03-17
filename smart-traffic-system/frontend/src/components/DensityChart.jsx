import React from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const DENSITY_COLORS = {
  A: "#60a5fa",
  B: "#34d399",
  C: "#f59e0b",
  D: "#f87171",
};

/**
 * @param {object} props
 * @param {Array}  props.data – array of density reading objects with {time, lane_id, density_score}
 */
export default function DensityChart({ data = [] }) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
        Waiting for density data…
      </div>
    );
  }

  // Group by time tick – pivot so each tick has a property per lane
  const pivoted = data.reduce((acc, reading) => {
    const existing = acc.find((r) => r.time === reading.time);
    const key = `Lane ${reading.lane_id}`;
    if (existing) {
      existing[key] = reading.density_score;
    } else {
      acc.push({ time: reading.time, [key]: reading.density_score });
    }
    return acc;
  }, []);

  const allLanes = [...new Set(data.map((d) => `Lane ${d.lane_id}`))];

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={pivoted} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="time" tick={{ fill: "#9ca3af", fontSize: 11 }} />
        <YAxis
          domain={[0, 1]}
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          tick={{ fill: "#9ca3af", fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151" }}
          formatter={(val) => `${(val * 100).toFixed(1)}%`}
        />
        <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />
        {allLanes.map((lane, i) => (
          <Line
            key={lane}
            type="monotone"
            dataKey={lane}
            stroke={Object.values(DENSITY_COLORS)[i % 4]}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
