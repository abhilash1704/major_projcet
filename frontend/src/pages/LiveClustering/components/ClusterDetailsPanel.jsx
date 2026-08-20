/**
 * ClusterDetailsPanel.jsx — Detailed Inspection Popup/Modal for a Selected DBSCAN Cluster
 */
import { X, Car, Users, Gauge, Compass, MapPin, ShieldCheck } from "lucide-react";
import { useLiveClustering } from "../context/LiveClusteringContext";

export const ClusterDetailsPanel = () => {
  const { selectedCluster, setSelectedCluster, evaluation } = useLiveClustering();

  if (!selectedCluster) return null;

  const userCount = selectedCluster.user_count || selectedCluster.size || (selectedCluster.user_ids ? selectedCluster.user_ids.length : 0);
  const avgSpeed = selectedCluster.average_speed_kmh ?? selectedCluster.avg_speed_kmh ?? 0;
  const avgHeading = selectedCluster.average_heading ?? selectedCluster.avg_heading ?? 0;
  const roadEdge = selectedCluster.primary_road_edge_id || selectedCluster.road_edge_id || "Unmapped";
  const purity = evaluation?.cluster_purity ? (evaluation.cluster_purity * 100).toFixed(0) : "100";

  return (
    <div className="absolute bottom-6 left-6 z-40 w-80 bg-white/95 dark:bg-surface-dark/95 backdrop-blur-md border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-xl flex flex-col gap-3 animate-in fade-in slide-in-from-bottom-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
          <h4 className="text-sm font-bold text-slate-900 dark:text-white font-mono">
            CLUSTER {selectedCluster.cluster_id}
          </h4>
        </div>
        <button
          onClick={() => setSelectedCluster(null)}
          className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Primary Attributes Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="p-2 bg-slate-50 dark:bg-slate-900/60 rounded-lg border border-slate-200/60 dark:border-slate-800 flex flex-col">
          <span className="text-[10px] text-slate-400 font-medium flex items-center gap-1">
            <Users className="w-3 h-3 text-indigo-500" /> Users Grouped
          </span>
          <span className="text-base font-bold text-slate-900 dark:text-white mt-0.5">{userCount}</span>
        </div>

        <div className="p-2 bg-emerald-50/50 dark:bg-emerald-950/20 rounded-lg border border-emerald-200/60 dark:border-emerald-900/40 flex flex-col">
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
            <Car className="w-3 h-3 text-emerald-500" /> Estimated Vehicle
          </span>
          <span className="text-base font-bold text-emerald-700 dark:text-emerald-300 mt-0.5">1</span>
        </div>

        <div className="p-2 bg-slate-50 dark:bg-slate-900/60 rounded-lg border border-slate-200/60 dark:border-slate-800 flex flex-col">
          <span className="text-[10px] text-slate-400 font-medium flex items-center gap-1">
            <Gauge className="w-3 h-3 text-amber-500" /> Average Speed
          </span>
          <span className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{avgSpeed} km/h</span>
        </div>

        <div className="p-2 bg-slate-50 dark:bg-slate-900/60 rounded-lg border border-slate-200/60 dark:border-slate-800 flex flex-col">
          <span className="text-[10px] text-slate-400 font-medium flex items-center gap-1">
            <Compass className="w-3 h-3 text-sky-500" /> Heading
          </span>
          <span className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{avgHeading}°</span>
        </div>
      </div>

      {/* Road Edge & Purity */}
      <div className="flex flex-col gap-1.5 pt-1 border-t border-slate-100 dark:border-slate-800/80 text-xs">
        <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
          <span className="flex items-center gap-1 text-[11px]">
            <MapPin className="w-3.5 h-3.5 text-purple-500" /> Road Edge:
          </span>
          <span className="font-mono text-[11px] font-semibold text-slate-800 dark:text-slate-200 truncate max-w-[140px]">
            {roadEdge}
          </span>
        </div>

        <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
          <span className="flex items-center gap-1 text-[11px]">
            <ShieldCheck className="w-3.5 h-3.5 text-teal-500" /> Cluster Purity:
          </span>
          <span className="font-mono text-[11px] font-bold text-teal-600 dark:text-teal-400">
            {purity}%
          </span>
        </div>
      </div>
    </div>
  );
};
