import { Marker, Popup, CircleMarker } from "react-leaflet";
import L from "leaflet";
import { useNavigationEngineContext } from "../../context/NavigationEngineContext";

/**
 * isValidLocation
 * Guard against null / missing / non-finite coordinates.
 */
function isValidLocation(loc) {
  if (!loc) return false;
  const lat = Number(loc.latitude ?? (Array.isArray(loc) ? loc[0] : undefined));
  const lng = Number(loc.longitude ?? (Array.isArray(loc) ? loc[1] : undefined));
  return isFinite(lat) && isFinite(lng) && lat !== 0 && lng !== 0;
}

/**
 * toLatLng
 * Convert a normalised location object OR a [lat,lng] array to a Leaflet position.
 */
function toLatLng(loc) {
  if (Array.isArray(loc)) return loc;
  return [Number(loc.latitude), Number(loc.longitude)];
}

// Custom red pin icon using a Leaflet DivIcon
const destinationIcon = L.divIcon({
  className: "",
  html: `
    <div style="
      width: 28px;
      height: 28px;
      background: #dc2626;
      border: 3px solid #ffffff;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      box-shadow: 0 2px 8px rgba(220,38,38,0.5);
    "></div>
  `,
  iconSize: [28, 28],
  iconAnchor: [14, 28],
  popupAnchor: [0, -30],
});

/**
 * DestinationMarker — Phase 4.3
 *
 * Renders a red pin at the selected destination location.
 * Reads destinationLocation directly from NavigationContext.
 * Returns null when no valid destination is selected.
 */
export const DestinationMarker = () => {
  const { destinationLocation } = useNavigationEngineContext();

  if (!isValidLocation(destinationLocation)) return null;

  const position = toLatLng(destinationLocation);
  const name = destinationLocation?.displayName ?? "Destination";

  return (
    <>
      {/* Accuracy ring */}
      <CircleMarker
        center={position}
        radius={16}
        pathOptions={{
          fillColor: "#dc2626",
          fillOpacity: 0.12,
          color: "#dc2626",
          weight: 1.5,
        }}
      />

      {/* Pin marker */}
      <Marker position={position} icon={destinationIcon}>
        <Popup autoPan={true} maxWidth={220}>
          <div className="text-xs p-0.5">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="w-2.5 h-2.5 rounded-full bg-red-600 shrink-0" />
              <span className="font-bold text-slate-800">Destination</span>
            </div>
            <p className="text-slate-600 leading-snug">{name}</p>
          </div>
        </Popup>
      </Marker>
    </>
  );
};
