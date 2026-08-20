import { Activity, Car, AlertTriangle, MapPin, Layers, Clock, RefreshCw } from "lucide-react";
import { useState, useEffect } from "react";
import { InfoCard } from "./InfoCard";
import { useNavigationEngineContext } from "../../navigation-engine/context/NavigationEngineContext";
import { useLayers } from "../../navigation-engine/hooks/useLayers";

// Helper to format relative time
const getRelativeTime = (date) => {
  if (!date) return "N/A";
  const seconds = Math.round((new Date() - date) / 1000);
  if (seconds < 2) return "Just now";
  if (seconds < 60) return `${seconds} sec ago`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes} min ago`;
};

export const TrafficCard = () => {
  const {
    vehicles,
    hotspotsData,
    hotspotsError,
    isTrafficUpdating,
    trafficLastUpdated,
  } = useNavigationEngineContext();
  const { isLayerActive, toggleLayer } = useLayers();
  
  const [timeText, setTimeText] = useState(getRelativeTime(trafficLastUpdated));

  useEffect(() => {
    // Update relative time every second
    const interval = setInterval(() => {
      setTimeText(getRelativeTime(trafficLastUpdated));
    }, 1000);
    return () => clearInterval(interval);
  }, [trafficLastUpdated]);

  const isTrafficActive = isLayerActive("traffic");
  const isClusterActive = isLayerActive("cluster");

  const activeVehicleCount = vehicles ? vehicles.length : 0;
  const isSimulationActive = activeVehicleCount > 0;
  const hotspotCount = isSimulationActive && hotspotsData ? (hotspotsData.hotspot_count ?? 0) : 0;
  
  // Authoritative global traffic level from backend hotspots response
  const trafficLevelText = isSimulationActive && hotspotsData ? (hotspotsData.global_traffic_level || "LOW") : "N/A";

  const severityColors = {
    HIGH: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    MEDIUM: "bg-warning/15 text-warning dark:bg-warning/20",
    LOW: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
  };

  const getStatusDisplay = () => {
    if ((!isTrafficActive && !isClusterActive) || !isSimulationActive) return null;
    if (hotspotsError) {
      return <span className="text-xs font-semibold text-red-500">Error</span>;
    }
    if (isTrafficUpdating) {
      return (
        <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
          <RefreshCw size={12} className="animate-spin" /> Updating...
        </span>
      );
    }
    if (hotspotsData) {
      return (
        <span className="text-xs font-semibold text-green-500 flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span> LIVE
        </span>
      );
    }
    return null;
  };

  return (
    <InfoCard title="Traffic Summary" icon={Activity} subtitle="Real-time Hotspots" status={getStatusDisplay()}>
      <div className="space-y-4">
        {hotspotsError && (isTrafficActive || isClusterActive) && isSimulationActive && (
          <div className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 p-2 rounded-lg">
            Traffic data temporarily unavailable.
          </div>
        )}

        <div className="flex items-center justify-between">
          <span className="text-slate-500 dark:text-slate-400 font-medium text-sm">Traffic Level</span>
          <span className={`px-2.5 py-1 font-bold text-xs rounded-lg flex items-center gap-1 ${isSimulationActive && hotspotsData ? severityColors[trafficLevelText] || 'bg-slate-100 text-slate-500 dark:bg-slate-800' : 'bg-slate-100 text-slate-500 dark:bg-slate-800'}`}>
            <AlertTriangle size={13} /> {isSimulationActive ? trafficLevelText : "N/A"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-1">
          <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-xl border border-slate-100 dark:border-slate-700/60">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 font-medium mb-1">
              <Car size={14} className="text-primary" /> Active Vehicles
            </div>
            <div className="text-xl font-bold text-slate-900 dark:text-white">
              {isSimulationActive ? activeVehicleCount : "-"}
            </div>
          </div>

          <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-xl border border-slate-100 dark:border-slate-700/60">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 font-medium mb-1">
              <MapPin size={14} className="text-primary" /> Hotspots
            </div>
            <div className="text-xl font-bold text-slate-900 dark:text-white">
              {isSimulationActive ? hotspotCount : "-"}
            </div>
          </div>
        </div>
        
        {isSimulationActive && (
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Clock size={12} /> Last Updated: {timeText}
          </div>
        )}

        {/* Legend */}
        {(isTrafficActive || isClusterActive) && (
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mt-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-blue-500"></div> Cluster
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-orange-500"></div> Medium
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-red-500"></div> High
            </div>
          </div>
        )}

        {/* Visibility Toggles */}
        <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <Layers size={14} /> Map Visualization
            </div>
            <button 
              onClick={() => toggleLayer("traffic")}
              className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${isTrafficActive ? 'bg-primary text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400'}`}
            >
              {isTrafficActive ? 'ON' : 'OFF'}
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <Layers size={14} /> Clustering View
            </div>
            <button 
              onClick={() => toggleLayer("cluster")}
              className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${isClusterActive ? 'bg-primary text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400'}`}
            >
              {isClusterActive ? 'ON' : 'OFF'}
            </button>
          </div>
        </div>
        
      </div>
    </InfoCard>
  );
};


