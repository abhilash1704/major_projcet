import { useMemo } from "react";
import { Marker, Tooltip } from "react-leaflet";
import L from "leaflet";

/**
 * VehicleMarker — Sprint 4.4
 *
 * Renders a single vehicle on the Leaflet map using a lightweight DivIcon.
 * - Small 10×10px amber dot with heading arrow (rotatable).
 * - Shows vehicle_id on hover in debug builds.
 * - Does NOT use external CDN images.
 *
 * @param {Object} props
 * @param {string|number} props.vehicleId
 * @param {number}  props.lat
 * @param {number}  props.lon
 * @param {number}  props.heading  degrees clockwise from north
 * @param {string}  props.status   "active" | "stopped"
 */
export const VehicleMarker = ({ vehicleId, lat, lon, heading = 0, status = "active" }) => {
  const isActive = status === "active";
  const color = isActive ? "#f59e0b" : "#6b7280"; // amber-400 for active, gray-500 for stopped

  const icon = useMemo(
    () =>
      L.divIcon({
        className: "",
        html: `
          <div style="
            position: relative;
            width: 12px;
            height: 12px;
            transform: rotate(${heading}deg);
          ">
            <!-- Body dot -->
            <div style="
              width: 10px;
              height: 10px;
              background: ${color};
              border: 1.5px solid rgba(255,255,255,0.85);
              border-radius: 50%;
              box-shadow: 0 0 4px rgba(0,0,0,0.35);
              position: absolute;
              top: 1px;
              left: 1px;
            "></div>
            <!-- Heading indicator (tiny triangle at top) -->
            <div style="
              position: absolute;
              top: -4px;
              left: 3.5px;
              width: 0;
              height: 0;
              border-left: 2.5px solid transparent;
              border-right: 2.5px solid transparent;
              border-bottom: 5px solid ${color};
              opacity: 0.9;
            "></div>
          </div>
        `,
        iconSize: [12, 12],
        iconAnchor: [6, 6],
      }),
    [color, heading]
  );

  if (!isFinite(lat) || !isFinite(lon)) return null;

  return (
    <Marker position={[lat, lon]} icon={icon}>
      <Tooltip direction="top" offset={[0, -8]} opacity={0.92} sticky={false}>
        <span style={{ fontSize: "10px", fontFamily: "monospace" }}>
          #{String(vehicleId).slice(-6)} · {status}
        </span>
      </Tooltip>
    </Marker>
  );
};
