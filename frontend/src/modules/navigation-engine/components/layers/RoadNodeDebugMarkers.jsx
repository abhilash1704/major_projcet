import { CircleMarker, Popup } from "react-leaflet";
import { useNavigationEngineContext } from "../../context/NavigationEngineContext";

/**
 * RoadNodeDebugMarkers — Sprint 5.4
 *
 * Development-only visual debug layer rendering small dots at the exact
 * snapped Road Network Node locations. Only visible when isDebugMode is true.
 */
export const RoadNodeDebugMarkers = () => {
  const { sourceRoadNode, destinationRoadNode, isDebugMode } = useNavigationEngineContext();

  if (!isDebugMode) return null;

  return (
    <>
      {sourceRoadNode && isFinite(sourceRoadNode.latitude) && isFinite(sourceRoadNode.longitude) && (
        <CircleMarker
          center={[sourceRoadNode.latitude, sourceRoadNode.longitude]}
          radius={6}
          pathOptions={{
            color: "#06b6d4",
            fillColor: "#22d3ee",
            fillOpacity: 0.9,
            weight: 2,
            dashArray: "3, 3"
          }}
        >
          <Popup>
            <div className="text-xs">
              <span className="font-bold text-cyan-700">Nearest Source Road Node</span>
              <div>ID: #{sourceRoadNode.nodeId}</div>
              <div>Snap Distance: {Math.round(sourceRoadNode.distance * 1000)} meters</div>
            </div>
          </Popup>
        </CircleMarker>
      )}

      {destinationRoadNode && isFinite(destinationRoadNode.latitude) && isFinite(destinationRoadNode.longitude) && (
        <CircleMarker
          center={[destinationRoadNode.latitude, destinationRoadNode.longitude]}
          radius={6}
          pathOptions={{
            color: "#a855f7",
            fillColor: "#c084fc",
            fillOpacity: 0.9,
            weight: 2,
            dashArray: "3, 3"
          }}
        >
          <Popup>
            <div className="text-xs">
              <span className="font-bold text-purple-700">Nearest Destination Road Node</span>
              <div>ID: #{destinationRoadNode.nodeId}</div>
              <div>Snap Distance: {Math.round(destinationRoadNode.distance * 1000)} meters</div>
            </div>
          </Popup>
        </CircleMarker>
      )}
    </>
  );
};
