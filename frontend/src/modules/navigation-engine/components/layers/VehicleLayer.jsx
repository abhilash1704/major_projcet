import { useNavigationEngineContext } from "../../context/NavigationEngineContext";
import { VehicleMarker } from "./VehicleMarker";

/**
 * VehicleLayer — Sprint 4.4
 *
 * Renders all simulated vehicles onto the existing Leaflet map.
 * Reads vehicle state from NavigationEngineContext — no separate map, no duplicate layer.
 *
 * Performance:
 * - Vehicles are keyed by vehicle_id for stable React reconciliation.
 * - No layer destruction on position update — markers are updated in-place.
 * - Skips vehicles with invalid coordinates silently.
 */
export const VehicleLayer = () => {
  const { vehicles } = useNavigationEngineContext();

  if (!vehicles || vehicles.length === 0) return null;

  return (
    <>
      {vehicles.map((v) => {
        const lat = Number(v.latitude);
        const lon = Number(v.longitude);

        if (!isFinite(lat) || !isFinite(lon) || lat === 0 || lon === 0) return null;

        return (
          <VehicleMarker
            key={v.vehicle_id}
            vehicleId={v.vehicle_id}
            lat={lat}
            lon={lon}
            heading={Number(v.heading) || 0}
            status={v.status || "active"}
          />
        );
      })}
    </>
  );
};
