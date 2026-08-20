import { SearchOverlay } from "./overlays/SearchOverlay";
import { TrafficOverlay } from "./overlays/TrafficOverlay";
import { VehicleOverlay } from "./overlays/VehicleOverlay";
import { ClusterOverlay } from "./overlays/ClusterOverlay";
import { RouteOverlay } from "./overlays/RouteOverlay";
import { useOverlays } from "../hooks/useOverlays";

/**
 * OverlayManager Component
 * Registers UI overlays, maintains rendering order, and manages overlay visibility
 */
export const OverlayManager = ({ children }) => {
  const { isOverlayActive } = useOverlays();

  return (
    <div className="absolute inset-0 pointer-events-none z-[1000]">
      {isOverlayActive("search") && <SearchOverlay />}
      {isOverlayActive("traffic") && <TrafficOverlay />}
      {isOverlayActive("vehicle") && <VehicleOverlay />}
      {isOverlayActive("cluster") && <ClusterOverlay />}
      {isOverlayActive("route") && <RouteOverlay />}
      {children}
    </div>
  );
};
