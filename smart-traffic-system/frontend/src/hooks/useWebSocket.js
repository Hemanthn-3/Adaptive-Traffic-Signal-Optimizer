import { useState, useEffect, useCallback, useRef } from "react";
import { WS_URL } from "../config";

const RECONNECT_DELAY = 3000;

export function useWebSocket() {
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [densityData, setDensityData] = useState(null);
  const [signalData, setSignalData] = useState(null);
  const [emergencyData, setEmergencyData] = useState(null);
  const [isEmergency, setIsEmergency] = useState(false);
  const [densityHistory, setDensityHistory] = useState([]);
  // Per-intersection live data map: { "INT-01": {...}, "INT-02": {...}, ... }
  const [allIntersectionData, setAllIntersectionData] = useState({});

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      clearTimeout(reconnectTimer.current);
    };

    ws.onmessage = (evt) => {
      let msg;
      try { msg = JSON.parse(evt.data); } catch { return; }

      const { type, data, intersection_id } = msg;

      if (type === "density_update") {
        // Update per-intersection map
        if (intersection_id) {
          setAllIntersectionData(prev => ({
            ...prev,
            [intersection_id]: { ...data, id: intersection_id },
          }));
        }
        // Also set the flat densityData (for backward compat / selected intersection)
        setDensityData(data);
        setDensityHistory(prev => {
          const next = [
            ...prev,
            {
              time: new Date().toLocaleTimeString("en", { hour12: false }),
              laneA: data?.lane_a_density ?? 0,
              laneB: data?.lane_b_density ?? 0,
            },
          ];
          return next.slice(-60);
        });
      } else if (type === "signal_update") {
        setSignalData(data);
        if (data.is_emergency === true) {
          setIsEmergency(true);
        } else if (data.is_emergency === false) {
          setIsEmergency(false);
        }
      } else if (type === "emergency_alert") {
        // Force signal state to full-green override immediately so the
        // Dashboard countdown and phase logic update without waiting for
        // a follow-up signal_update (avoids race-condition blank state).
        setSignalData(prev => ({
          ...prev,
          lane_a_green: 90,
          lane_b_green: 90,
          lane_a_red: 0,
          lane_b_red: 0,
          lane_a_green_seconds: 90,
          lane_b_green_seconds: 90,
          lane_a_red_seconds: 0,
          lane_b_red_seconds: 0,
          lane_a_state: "green",
          lane_b_state: "green",
          cycle_time: 90,
          reason: "EMERGENCY — Ambulance corridor active",
          optimization_reason: "EMERGENCY — Ambulance corridor active",
          is_emergency: true,
          is_emergency_override: true,
        }));
        setEmergencyData(data);
        setIsEmergency(true);
      } else if (type === "emergency_clear") {
        // Reset emergency flag on signal data; normal signal_update will
        // arrive shortly and overwrite the rest.
        setSignalData(prev => prev ? { ...prev, is_emergency: false, is_emergency_override: false } : prev);
        setEmergencyData(null);
        setIsEmergency(false);
      }

      // ping / init are intentionally ignored
    };

    ws.onclose = () => {
      setIsConnected(false);
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return {
    densityData,
    signalData,
    emergencyData,
    isEmergency,
    densityHistory,
    isConnected,
    sendMessage,
    allIntersectionData,
  };
}
