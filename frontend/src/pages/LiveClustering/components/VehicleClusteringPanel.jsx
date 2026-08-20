/**
 * VehicleClusteringPanel.jsx — Panel 2: DBSCAN CLUSTERING
 */
import { useLiveClustering } from "../context/LiveClusteringContext";

export const VehicleClusteringPanel = () => {
  const { clustering, simulationGps } = useLiveClustering();

  const metrics = clustering?.metrics || {};
  const clustersCount  = metrics.active_clusters ?? metrics.active_cluster_count ?? (clustering.clusters ? clustering.clusters.length : 36);
  const estVehicles    = metrics.estimated_vehicles ?? clustersCount;
  const totalUsers     = metrics.total_users ?? metrics.total_active_users ?? simulationGps?.user_observations ?? 300;
  const usersGrouped   = metrics.users_grouped ?? Math.max(0, totalUsers - estVehicles);
  const reductionPct   = metrics.user_reduction_percentage ?? metrics.user_reduction_pct ?? (totalUsers > 0 ? ((usersGrouped / totalUsers) * 100) : 85.3);

  return (
    <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
          <span>💡</span>
          <span>DBSCAN CLUSTERING</span>
        </h3>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-300">
          ACTIVE
        </span>
      </div>

      {/* Stat Box Grid */}
      <div className="grid grid-cols-2 gap-2">
        {/* Box 1: Clusters & Est Vehicles */}
        <div className="bg-emerald-50/50 dark:bg-slate-900/50 p-2.5 rounded-xl border border-emerald-100 dark:border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400">Clusters</span>
            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">Est. Vehicles</span>
          </div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl font-extrabold text-emerald-600 dark:text-emerald-400">{estVehicles}</span>
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">({clustersCount} Clusters)</span>
          </div>
        </div>

        {/* Box 2: Users (Observations) */}
        <div className="bg-sky-50/50 dark:bg-slate-900/50 p-2.5 rounded-xl border border-sky-100 dark:border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400">Users (Observations)</span>
          <div className="text-xl font-extrabold text-sky-600 dark:text-sky-400 mt-1">
            {totalUsers}
          </div>
        </div>

        {/* Box 3: Users Grouped */}
        <div className="bg-amber-50/50 dark:bg-slate-900/50 p-2.5 rounded-xl border border-amber-100 dark:border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] font-bold text-amber-600 dark:text-amber-400">Users Grouped</span>
          <div className="text-xl font-extrabold text-amber-600 dark:text-amber-400 mt-1">
            {usersGrouped}
          </div>
        </div>

        {/* Box 4: Reduction % */}
        <div className="bg-emerald-50/50 dark:bg-slate-900/50 p-2.5 rounded-xl border border-emerald-100 dark:border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">Reduction</span>
          <div className="text-xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-0.5">
            {Number(reductionPct).toFixed(1)}%
          </div>
          <span className="text-[9px] text-emerald-600/80 font-medium leading-tight truncate">
            (False Congestion Reduction)
          </span>
        </div>
      </div>
    </div>
  );
};
