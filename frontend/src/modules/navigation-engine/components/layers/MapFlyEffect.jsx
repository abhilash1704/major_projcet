import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { useNavigationEngineContext } from "../../context/NavigationEngineContext";

const SELECTION_ZOOM = 14;    // zoom when a single location is selected
const BOUNDS_PADDING = [80, 80]; // px padding so markers clear the panels

/**
 * isValidLocation — shared guard
 */
function isValidLocation(loc) {
  if (!loc) return false;
  const lat = Number(loc.latitude ?? (Array.isArray(loc) ? loc[0] : undefined));
  const lng = Number(loc.longitude ?? (Array.isArray(loc) ? loc[1] : undefined));
  return isFinite(lat) && isFinite(lng) && lat !== 0 && lng !== 0;
}

function toLatLng(loc) {
  if (Array.isArray(loc)) return [loc[0], loc[1]];
  return [Number(loc.latitude), Number(loc.longitude)];
}

/**
 * MapFlyEffect — Phase 4.3
 *
 * A render-less component that lives inside <LeafletMapContainer>.
 * Watches sourceLocation and destinationLocation in NavigationContext and
 * imperatively controls the Leaflet map camera:
 *
 *  - Only source selected  → flyTo source at SELECTION_ZOOM
 *  - Only dest selected    → flyTo dest at SELECTION_ZOOM
 *  - Both selected         → fitBounds with padding so both markers are visible
 *
 * This is the ONLY place that moves the map in response to search selections.
 * It does NOT draw routes.
 */
export const MapFlyEffect = () => {
  const map = useMap();
  const { sourceLocation, destinationLocation } = useNavigationEngineContext();

  const srcValid = isValidLocation(sourceLocation);
  const destValid = isValidLocation(destinationLocation);

  // When sourceLocation changes
  useEffect(() => {
    if (!srcValid) return;
    if (destValid) {
      // Both exist → fitBounds handles it in the combined effect below
      return;
    }
    // Only source selected — fly to it
    try {
      map.flyTo(toLatLng(sourceLocation), SELECTION_ZOOM, { duration: 1.2 });
    } catch {
      // Map may not be ready; silently ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceLocation]);

  // When destinationLocation changes
  useEffect(() => {
    if (!destValid) return;
    if (srcValid) {
      // Both exist — handled by the combined effect below
      return;
    }
    // Only destination selected — fly to it
    try {
      map.flyTo(toLatLng(destinationLocation), SELECTION_ZOOM, { duration: 1.2 });
    } catch {
      // silently ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [destinationLocation]);

  // When BOTH locations change — fitBounds
  useEffect(() => {
    if (!srcValid || !destValid) return;
    try {
      const bounds = L.latLngBounds([
        toLatLng(sourceLocation),
        toLatLng(destinationLocation),
      ]);
      map.fitBounds(bounds, {
        padding: BOUNDS_PADDING,
        maxZoom: 15,
        animate: true,
        duration: 1.2,
      });
    } catch {
      // silently ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceLocation, destinationLocation]);

  // Render nothing — this component is purely a side-effect controller
  return null;
};
