import { Marker, Popup, CircleMarker } from "react-leaflet";
import L from "leaflet";
import { useNavigationEngineContext } from "../../context/NavigationEngineContext";

/**
 * isValidLocation
 * Guard against null / missing / non-finite coordinates from Nominatim.
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

// Custom green pin icon using a Leaflet DivIcon so we don't depend on CDN images
const sourceIcon = L.divIcon({
  className: "",
  html: `
    <div style="
      width: 28px;
      height: 28px;
      background: #16a34a;
      border: 3px solid #ffffff;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      box-shadow: 0 2px 8px rgba(22,163,74,0.5);
    "></div>
  `,
  iconSize: [28, 28],
  iconAnchor: [14, 28],
  popupAnchor: [0, -30],
});

/**
 * SourceMarker — Phase 4.3
 *
 * Renders a green pin at the selected source location.
 * Reads sourceLocation directly from NavigationContext.
 * Returns null when no valid source is selected.
 */
export const SourceMarker = () => {
  const { sourceLocation } = useNavigationEngineContext();

  if (!isValidLocation(sourceLocation)) return null;

  const position = toLatLng(sourceLocation);
  const name = sourceLocation?.displayName ?? "Starting location";

  return (
    <>
      {/* Accuracy ring */}
      <CircleMarker
        center={position}
        radius={16}
        pathOptions={{
          fillColor: "#16a34a",
          fillOpacity: 0.12,
          color: "#16a34a",
          weight: 1.5,
        }}
      />

      {/* Pin marker */}
      <Marker position={position} icon={sourceIcon}>
        <Popup autoPan={true} maxWidth={220}>
          <div className="text-xs p-0.5">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="w-2.5 h-2.5 rounded-full bg-green-600 shrink-0" />
              <span className="font-bold text-slate-800">Start Location</span>
            </div>
            <p className="text-slate-600 leading-snug">{name}</p>
          </div>
        </Popup>
      </Marker>
    </>
  );
};
