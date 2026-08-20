import { MarkerLayer } from "./layers/MarkerLayer";
import { RouteLayer } from "./layers/RouteLayer";
import { TrafficLayer } from "./layers/TrafficLayer";
import { VehicleLayer } from "./layers/VehicleLayer";
import { ClusterLayer } from "./layers/ClusterLayer";
import { useLayers } from "../hooks/useLayers";

/**
 * LayerManager Component
 * Registers vector map layers, manages visibility, and provides scalable layer API
 */
export const LayerManager = () => {
  const { isLayerActive } = useLayers();

  return (
    <>
      {isLayerActive("cluster") && <ClusterLayer />}
      {isLayerActive("traffic") && <TrafficLayer />}
      {isLayerActive("route") && <RouteLayer />}
      {isLayerActive("vehicle") && <VehicleLayer />}
      {isLayerActive("marker") && <MarkerLayer />}
    </>
  );
};
