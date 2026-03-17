import React from "react";

/**
 * WaitTimeDisplay Component
 *
 * Shows average wait times per lane and total unique vehicles tracked.
 * Includes progress bars comparing wait time to typical cycle time (60 seconds).
 *
 * Props:
 *   avgWaitTimeLaneA : number (seconds)
 *   avgWaitTimeLaneB : number (seconds)
 *   uniqueVehicleCount : number
 *   cycleTime : number (seconds, default 60)
 */
export default function WaitTimeDisplay({
    avgWaitTimeLaneA = 0,
    avgWaitTimeLaneB = 0,
    uniqueVehicleCount = 0,
    cycleTime = 60,
}) {
    // Determine color based on wait time vs cycle time
    const getWaitColor = (waitTime) => {
        const ratio = waitTime / cycleTime;
        if (ratio < 0.5) return "#10b981"; // Green - good
        if (ratio < 1.0) return "#f59e0b"; // Amber - acceptable
        if (ratio < 1.5) return "#f97316"; // Orange - high
        return "#ef4444"; // Red - critical
    };

    const getWaitBgColor = (waitTime) => {
        const ratio = waitTime / cycleTime;
        if (ratio < 0.5) return "rgba(16, 185, 129, 0.1)";
        if (ratio < 1.0) return "rgba(245, 158, 11, 0.1)";
        if (ratio < 1.5) return "rgba(249, 115, 22, 0.1)";
        return "rgba(239, 68, 68, 0.1)";
    };

    return (
        <div
            className="rounded-lg p-5 border border-gray-800"
            style={{ background: "rgba(10, 15, 30, 0.6)" }}
        >
            <div className="mb-4">
                <p className="text-xs uppercase tracking-widest text-gray-500 mb-3">
                    Traffic Wait Times & Vehicle Tracking
                </p>
            </div>

            {/* Lane A */}
            <div className="mb-5">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-gray-300">Lane A</span>
                    <span
                        className="text-sm font-mono font-bold"
                        style={{ color: getWaitColor(avgWaitTimeLaneA) }}
                    >
                        {avgWaitTimeLaneA.toFixed(1)}s
                    </span>
                </div>
                <div
                    className="h-3 rounded-full overflow-hidden border border-gray-700"
                    style={{ background: "rgba(30, 30, 50)" }}
                >
                    <div
                        className="h-full transition-all duration-300"
                        style={{
                            width: `${Math.min((avgWaitTimeLaneA / cycleTime) * 100, 100)}%`,
                            background: getWaitColor(avgWaitTimeLaneA),
                            boxShadow: `0 0 12px ${getWaitColor(avgWaitTimeLaneA)}33`,
                        }}
                    />
                </div>
                <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>0s</span>
                    <span>{cycleTime}s (cycle)</span>
                </div>
            </div>

            {/* Lane B */}
            <div className="mb-5">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-gray-300">Lane B</span>
                    <span
                        className="text-sm font-mono font-bold"
                        style={{ color: getWaitColor(avgWaitTimeLaneB) }}
                    >
                        {avgWaitTimeLaneB.toFixed(1)}s
                    </span>
                </div>
                <div
                    className="h-3 rounded-full overflow-hidden border border-gray-700"
                    style={{ background: "rgba(30, 30, 50)" }}
                >
                    <div
                        className="h-full transition-all duration-300"
                        style={{
                            width: `${Math.min((avgWaitTimeLaneB / cycleTime) * 100, 100)}%`,
                            background: getWaitColor(avgWaitTimeLaneB),
                            boxShadow: `0 0 12px ${getWaitColor(avgWaitTimeLaneB)}33`,
                        }}
                    />
                </div>
                <div className="flex justify-between text-xs text-gray-600 mt-1">
                    <span>0s</span>
                    <span>{cycleTime}s (cycle)</span>
                </div>
            </div>

            {/* Unique vehicle count */}
            <div
                className="rounded-lg p-3 border border-gray-700"
                style={{ background: "rgba(0, 255, 136, 0.05)" }}
            >
                <div className="flex items-center justify-between">
                    <span className="text-xs uppercase tracking-widest text-gray-500">
                        Unique Vehicles Tracked
                    </span>
                    <span className="text-xl font-bold text-emerald-400">
                        {uniqueVehicleCount}
                    </span>
                </div>
            </div>

            {/* Status indicator */}
            <div className="mt-4 pt-4 border-t border-gray-800">
                {avgWaitTimeLaneA > cycleTime * 1.5 || avgWaitTimeLaneB > cycleTime * 1.5 ? (
                    <div className="flex items-center gap-2 text-xs text-orange-400">
                        <div className="w-2 h-2 rounded-full bg-orange-400 animate-pulse" />
                        <span>
                            {avgWaitTimeLaneA > cycleTime * 1.5 ? "Lane A" : "Lane B"} wait time{" "}
                            {Math.max(avgWaitTimeLaneA, avgWaitTimeLaneB) > cycleTime * 2
                                ? "CRITICAL"
                                : "HIGH"}
                        </span>
                    </div>
                ) : (
                    <div className="flex items-center gap-2 text-xs text-emerald-400">
                        <div className="w-2 h-2 rounded-full bg-emerald-400" />
                        <span>Wait times within acceptable range</span>
                    </div>
                )}
            </div>
        </div>
    );
}
