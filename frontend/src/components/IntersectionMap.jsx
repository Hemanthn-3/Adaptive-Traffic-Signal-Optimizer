import React from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Fix default icon paths broken by webpack/vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

const DENSITY_COLORS = {
  LOW: "#22c55e",
  MEDIUM: "#f97316",
  HIGH: "#ef4444",
  CRITICAL: "#7f1d1d",
};

/**
 * @param {object} props
 * @param {Array}  props.intersections  – from backend /api/traffic/intersections
 * @param {object} props.densityMap     – { lane_id: density_reading }
 * @param {Array}  props.emergencyRoute – array of intersection IDs in active corridor
 */
export default function IntersectionMap({ intersections = [], densityMap = {}, emergencyRoute = [] }) {
  const center = intersections.length > 0
    ? [intersections[0].latitude, intersections[0].longitude]
    : [12.9716, 77.5946]; // default: Bangalore

  return (
    <MapContainer center={center} zoom={14} className="w-full h-96 rounded-xl overflow-hidden">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {intersections.map((inter) => {
        const isOnRoute = emergencyRoute.includes(inter.id);
        return (
          <React.Fragment key={inter.id}>
            {isOnRoute && (
              <Circle
                center={[inter.latitude, inter.longitude]}
                radius={80}
                pathOptions={{ color: "#facc15", fillColor: "#facc15", fillOpacity: 0.3 }}
              />
            )}
            <Marker position={[inter.latitude, inter.longitude]}>
              <Popup>
                <strong>{inter.name}</strong><br />
                Lanes: {inter.num_lanes}
              </Popup>
            </Marker>
          </React.Fragment>
        );
      })}
    </MapContainer>
  );
}
