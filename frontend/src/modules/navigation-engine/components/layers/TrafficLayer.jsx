import { Circle, Popup, CircleMarker } from "react-leaflet";
import { useNavigationEngineContext } from "../../context/NavigationEngineContext";

const SEVERITY_COLORS = {
  HIGH: "#ef4444",   // Red
  MEDIUM: "#f97316", // Orange
  LOW: "#22c55e"     // Green
};

/**
 * TrafficLayer Component
 * Renders real-time traffic hotspots as interactive overlays.
 */
export const TrafficLayer = () => {
  const { hotspotsData, hotspotsError } = useNavigationEngineContext();

  if (hotspotsError || !hotspotsData || !hotspotsData.hotspots || hotspotsData.hotspot_count === 0) {
    return null;
  }

  return (
    <>
      {hotspotsData.hotspots.map((hotspot) => {
        const color = SEVERITY_COLORS[hotspot.severity] || SEVERITY_COLORS.LOW;
        const center = [hotspot.center_latitude, hotspot.center_longitude];
        
        return (
          <div key={`hotspot-group-${hotspot.hotspot_id || hotspot.cluster_id}`}>
            {/* The primary hotspot area circle */}
            <Circle
              center={center}
              radius={hotspot.radius_meters || 100}
              pathOptions={{
                color: color,
                fillColor: color,
                fillOpacity: 0.2,
                weight: 1,
              }}
            >
              <Popup>
                <div className="text-sm min-w-[150px]">
                  <div className="font-bold mb-1 border-b pb-1">Traffic Hotspot</div>
                  <div className="grid grid-cols-2 gap-x-2 gap-y-1">
                    <span className="text-slate-500">Severity:</span>
                    <span className="font-semibold" style={{ color }}>{hotspot.severity}</span>
                    
                    <span className="text-slate-500">Vehicles:</span>
                    <span className="font-medium">{hotspot.vehicle_count}</span>
                    
                    <span className="text-slate-500">Density:</span>
                    <span className="font-medium">{hotspot.density_vehicles_per_km2?.toFixed(1)} /km²</span>
                    
                    <span className="text-slate-500">Avg Speed:</span>
                    <span className="font-medium">{hotspot.average_speed_kmh?.toFixed(1)} km/h</span>
                    
                    <span className="text-slate-500">Radius:</span>
                    <span className="font-medium">{Math.round(hotspot.radius_meters)} m</span>
                    
                    <span className="text-slate-500">Score:</span>
                    <span className="font-medium">{hotspot.hotspot_score}</span>
                  </div>
                </div>
              </Popup>
            </Circle>
            
            {/* Center dot for visual clarity */}
            <CircleMarker
              center={center}
              radius={3}
              pathOptions={{
                color: "white",
                fillColor: color,
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
