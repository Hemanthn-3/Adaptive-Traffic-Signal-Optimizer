import React from "react";

/**
 * TrafficHeatmap.jsx
 * Shows heatmap of traffic density across intersections.
 * 
 * @param {object} props
 * @param {array} props.intersections - array of { id, name, density, vehicle_count }
 */

function getDensityColor(density) {
    if (density <= 30) return "#00ff88";    // Green
    if (density <= 60) return "#ffaa00";    // Yellow
    if (density <= 80) return "#ff6600";    // Orange
    return "#ff0000";                       // Red
}

function getDensityLevel(density) {
    if (density <= 30) return "LOW";
    if (density <= 60) return "MEDIUM";
    if (density <= 80) return "HIGH";
    return "V.HIGH";
}

export default function TrafficHeatmap({ intersections = [] }) {
    if (intersections.length === 0) {
        return (
            <div
                className="rounded-xl p-6 border flex items-center justify-center"
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    borderColor: "#374151",
                    minHeight: "250px",
                }}
            >
                <p className="text-gray-500 text-sm">No intersection data available</p>
            </div>
        );
    }

    return (
        <div
            className="rounded-xl p-4 border"
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                borderColor: "#374151",
            }}
        >
            <div className="flex items-center justify-between mb-4">
                <p className="text-xs uppercase tracking-widest text-gray-500">
                    Traffic Heatmap — Density by Intersection
                </p>
                {/* Legend */}
                <div className="flex items-center gap-2 text-xs">
                    <div className="flex items-center gap-1">
                        <div
                            className="w-3 h-3 rounded-full"
                            style={{ background: "#00ff88" }}
                        />
                        <span className="text-gray-600">Low</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div
                            className="w-3 h-3 rounded-full"
                            style={{ background: "#ffaa00" }}
                        />
                        <span className="text-gray-600">Med</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div
                            className="w-3 h-3 rounded-full"
                            style={{ background: "#ff6600" }}
                        />
                        <span className="text-gray-600">High</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <div
                            className="w-3 h-3 rounded-full"
                            style={{ background: "#ff0000" }}
                        />
                        <span className="text-gray-600">V. High</span>
                    </div>
                </div>
            </div>

            {/* Heatmap grid */}
            <div className="grid grid-cols-2 gap-3">
                {intersections.map((intersection) => {
                    const density = intersection.density || 0;
                    const color = getDensityColor(density);
                    const level = getDensityLevel(density);
                    const vehicleCount = intersection.vehicle_count || 0;
                    const circleSize = Math.min(20 + (vehicleCount / 10), 50);

                    return (
                        <div
                            key={intersection.id}
                            className="p-3 rounded-lg flex items-center gap-3"
                            style={{
                                background: "rgba(30,41,59,0.5)",
                                border: "1px solid #374151",
                            }}
                        >
                            {/* Circle sized by vehicle count */}
                            <div
                                className="rounded-full flex-shrink-0 flex items-center justify-center"
                                style={{
                                    width: `${circleSize}px`,
                                    height: `${circleSize}px`,
                                    background: color,
                                    opacity: 0.8,
                                    boxShadow: `0 0 12px ${color}80`,
                                }}
                            >
                                <span
                                    className="text-xs font-bold"
                                    style={{
                                        color: density > 50 ? "#0a0f1e" : "#0a0f1e",
                                        fontSize: circleSize > 35 ? "10px" : "8px",
                                    }}
                                >
                                    {vehicleCount}
                                </span>
                            </div>

                            {/* Intersection info */}
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-bold text-gray-200 truncate">
                                    {intersection.name}
                                </p>
                                <p className="text-xs text-gray-600 font-mono">
                                    {intersection.id}
                                </p>
                            </div>

                            {/* Density badge */}
                            <div
                                className="px-2 py-1 rounded text-xs font-bold text-center flex-shrink-0"
                                style={{
                                    background: color + "22",
                                    color: color,
                                }}
                            >
                                {density.toFixed(0)}%<br />{level}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
