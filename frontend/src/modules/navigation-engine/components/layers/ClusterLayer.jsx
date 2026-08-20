import { Circle, Popup, CircleMarker } from "react-leaflet";
import { useNavigationEngineContext } from "../../context/NavigationEngineContext";

const DENSITY_LEVEL_COLORS = {
  HIGH: "#ef4444",   // Red
  MEDIUM: "#f97316", // Orange
  LOW: "#3b82f6"     // Blue for dev/cluster view
};

/**
 * ClusterLayer Component
 * Renders spatial vehicle clusters for analysis/development view.
 * Hides clusters that are already rendered as active traffic hotspots.
 */
export const ClusterLayer = () => {
  const { clustersData, hotspotsData } = useNavigationEngineContext();

  if (!clustersData || !clustersData.clusters || clustersData.cluster_count === 0) {
    return null;
  }

  // Find all cluster IDs that are already designated as hotspots
  const hotspotClusterIds = new Set(
    (hotspotsData?.hotspots || []).map((h) => h.cluster_id)
  );

  return (
    <>
      {clustersData.clusters.map((cluster) => {
        // If a cluster is already a hotspot, suppress drawing the duplicate circle here
        if (hotspotClusterIds.has(cluster.cluster_id)) {
          return null;
        }

        const levelColor = DENSITY_LEVEL_COLORS[cluster.density_level] || DENSITY_LEVEL_COLORS.LOW;
        const center = [cluster.center_latitude, cluster.center_longitude];
        
        return (
          <div key={`cluster-group-${cluster.cluster_id}`}>
            {/* Dashed outer boundary for dev cluster representation */}
            <Circle
              center={center}
              radius={cluster.radius_meters || 100}
              pathOptions={{
                color: "#3b82f6", // Dev visualization color
                fillColor: "#3b82f6",
                fillOpacity: 0.08,
                weight: 1.5,
                dashArray: "6, 6"
              }}
            >
              <Popup>
                <div className="text-sm min-w-[150px] font-sans">
                  <div className="font-bold mb-1 border-b pb-1 text-blue-600">
                    Cluster #{cluster.cluster_id}
                  </div>
                  <div className="grid grid-cols-2 gap-x-2 gap-y-1">
                    <span className="text-slate-500">Vehicles:</span>
                    <span className="font-semibold text-slate-800">{cluster.vehicle_count}</span>
                    
                    <span className="text-slate-500">Density:</span>
                    <span className="font-medium text-slate-800">
                      {cluster.density_vehicles_per_km2?.toFixed(1)} /km²
                    </span>
                    
                    <span className="text-slate-500">Traffic:</span>
                    <span className="font-bold" style={{ color: levelColor }}>
                      {cluster.density_level}
                    </span>
                  </div>
                </div>
              </Popup>
            </Circle>
            
            {/* Center anchor for cluster */}
            <CircleMarker
              center={center}
              radius={3}
              pathOptions={{
                color: "white",
                fillColor: "#3b82f6",
                fillOpacity: 1,
                weight: 1,
              }}
              interactive={false}
            />
          </div>
        );
      })}
    </>
  );
};
