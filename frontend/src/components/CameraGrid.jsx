import React, { useState } from "react";

/**
 * CameraGrid.jsx
 * Shows 4 camera feeds status in a 2x2 grid.
 * 
 * @param {object} props
 * @param {array} props.cameras - array of camera objects with { id, direction, vehicle_count, density, status }
 * @param {function} props.onCameraClick - callback when camera card is clicked
 */

const DENSITY_COLORS = {
    low: { color: "#00ff88", bg: "rgba(0,255,136,0.08)" },
    medium: { color: "#ffaa00", bg: "rgba(255,170,0,0.08)" },
    high: { color: "#ff6600", bg: "rgba(255,102,0,0.08)" },
    critical: { color: "#ff4444", bg: "rgba(255,68,68,0.08)" },
};

function getDensityLevel(density) {
    if (density <= 30) return "low";
    if (density <= 60) return "medium";
    if (density <= 80) return "high";
    return "critical";
}

function CameraCard({ camera, onClick }) {
    const level = getDensityLevel(camera.density || 0);
    const levelMeta = DENSITY_COLORS[level];
    const isActive = camera.status === "active";

    return (
        <div
            onClick={() => onClick?.(camera)}
            className="rounded-xl p-4 border cursor-pointer transition-all hover:border-opacity-60"
            style={{
                background: "rgba(15, 23, 42, 0.6)",
                borderColor: isActive ? "#374151" : "#1f2d44",
                borderWidth: "1px",
            }}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div>
                    <p className="text-sm font-bold" style={{ color: "#e5e7eb" }}>
                        {camera.direction || "Unknown"}
                    </p>
                    <p className="text-xs text-gray-600 font-mono">{camera.id}</p>
                </div>
                <span
                    className="px-2 py-1 rounded-full text-xs font-bold"
                    style={{
                        background: isActive ? "rgba(0,255,136,0.15)" : "rgba(107,114,128,0.15)",
                        color: isActive ? "#00ff88" : "#9ca3af",
                    }}
                >
                    {isActive ? "ACTIVE" : "IDLE"}
                </span>
            </div>

            {/* Vehicle count */}
            <div className="flex items-baseline gap-1 mb-3">
                <p className="font-mono text-2xl font-bold" style={{ color: isActive ? "#e5e7eb" : "#6b7280" }}>
                    {camera.vehicle_count || 0}
                </p>
                <p className="text-xs text-gray-600">vehicles</p>
            </div>

            {/* Density bar */}
            <div className="mb-2">
                <div className="flex items-center justify-between mb-1">
                    <p className="text-xs text-gray-600">Density</p>
                    <span className="text-xs font-mono" style={{ color: levelMeta.color }}>
                        {(camera.density || 0).toFixed(0)}%
                    </span>
                </div>
                <div className="w-full h-2 rounded-full bg-gray-800 overflow-hidden">
                    <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{
                            width: `${Math.min(camera.density || 0, 100)}%`,
                            background: levelMeta.color,
                        }}
                    />
                </div>
            </div>

            {/* Density badge */}
            <div
                className="px-2 py-1 rounded-lg text-xs font-bold text-center"
                style={{
                    background: levelMeta.bg,
                    color: levelMeta.color,
                }}
            >
                {level.toUpperCase()}
            </div>

            {/* Last update */}
            {camera.last_updated && (
                <p className="text-xs text-gray-700 mt-2 text-center font-mono">
                    Updated {new Date(camera.last_updated).toLocaleTimeString()}
                </p>
            )}
        </div>
    );
}

export default function CameraGrid({ cameras = [], onCameraClick = () => { } }) {
    if (cameras.length === 0) {
        return (
            <div
                className="rounded-xl p-6 border flex items-center justify-center"
                style={{
                    background: "rgba(15, 23, 42, 0.6)",
                    borderColor: "#374151",
                    minHeight: "300px",
                }}
            >
                <p className="text-gray-500 text-sm">No camera data available</p>
            </div>
        );
    }

    // Ensure 4 cameras (car_1 to cam_4)
    const cameraIds = ["cam_1", "cam_2", "cam_3", "cam_4"];
    const directionNames = ["North", "South", "East", "West"];

    const cameraMap = (cameras || []).reduce((acc, cam) => {
        acc[cam.id] = cam;
        return acc;
    }, {});

    const displayCameras = cameraIds.map((id, idx) => {
        const cam = cameraMap[id];
        return cam || {
            id,
            direction: directionNames[idx],
            vehicle_count: 0,
            density: 0,
            status: "idle",
        };
    });

    return (
        <div className="grid grid-cols-2 gap-4">
            {displayCameras.map((camera) => (
                <CameraCard
                    key={camera.id}
                    camera={camera}
                    onClick={onCameraClick}
                />
            ))}
        </div>
    );
}
