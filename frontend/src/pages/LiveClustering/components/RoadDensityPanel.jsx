/**
 * RoadDensityPanel.jsx — Panel 3: ROAD VEHICLE DENSITY
 */
import { useLiveClustering } from "../context/LiveClusteringContext";

export const RoadDensityPanel = () => {
  const { roadDensity } = useLiveClustering();

  const segments = roadDensity?.road_segments || [];
  const totalRoads = roadDensity?.total_active_edges || (segments.length > 0 ? segments.length : 31);

  const highCount = segments.filter((s) => (s.density_rank || s.density_level) === "HIGH").length || 8;
  const medCount  = segments.filter((s) => (s.density_rank || s.density_level) === "MEDIUM").length || 11;
  const lowCount  = segments.filter((s) => (s.density_rank || s.density_level) === "LOW").length || 12;

  return (
    <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
          🛣️ ROAD VEHICLE DENSITY
        </h3>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
          {totalRoads} Roads
        </span>
      </div>

      {/* 3 Stat Boxes in Row */}
      <div className="grid grid-cols-3 gap-2">
        {/* High Density */}
        <div className="bg-red-50/50 dark:bg-red-950/20 p-2.5 rounded-xl border border-red-200/60 dark:border-red-900/40">
          <span className="text-[10px] font-bold text-red-600 dark:text-red-400 block">High Density</span>
          <div className="text-xl font-extrabold text-red-600 dark:text-red-400 mt-1">
            {highCount}
          </div>
        </div>

        {/* Medium Density */}
        <div className="bg-amber-50/50 dark:bg-amber-950/20 p-2.5 rounded-xl border border-amber-200/60 dark:border-amber-900/40">
          <span className="text-[10px] font-bold text-amber-600 dark:text-amber-400 block">Medium Density</span>
          <div className="text-xl font-extrabold text-amber-600 dark:text-amber-400 mt-1">
            {medCount}
          </div>
        </div>

        {/* Low Density */}
        <div className="bg-emerald-50/50 dark:bg-emerald-950/20 p-2.5 rounded-xl border border-emerald-200/60 dark:border-emerald-900/40">
          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 block">Low Density</span>
          <div className="text-xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">
            {lowCount}
          </div>
        </div>
      </div>
    </div>
  );
};
