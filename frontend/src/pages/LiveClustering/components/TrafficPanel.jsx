/**
 * TrafficPanel.jsx — Panel 5: REAL TRAFFIC (EXTERNAL PROVIDER) & Sidebar Footer
 */
import { useLiveClustering } from "../context/LiveClusteringContext";
import { RefreshCw } from "lucide-react";

export const TrafficPanel = () => {
  const { realTraffic } = useLiveClustering();

  const currentSpeed  = realTraffic?.current_speed_kmh ?? realTraffic?.avg_speed_kmh ?? 24;
  const freeFlowSpeed = realTraffic?.free_flow_speed_kmh ?? 42;
  const condition     = realTraffic?.traffic_condition ?? realTraffic?.severity ?? "MEDIUM";
  const status        = realTraffic?.status || "LIVE";

  const currentTimeStr = new Date().toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div className="space-y-3">
      {/* Panel 5 Card */}
      <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
            🚦 REAL TRAFFIC (EXTERNAL PROVIDER)
          </h3>
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-300">
            {status}
          </span>
        </div>

        {/* 3 Stat Boxes in Row */}
        <div className="grid grid-cols-3 gap-2">
          {/* Current Speed */}
          <div className="bg-slate-50 dark:bg-slate-900/50 p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800">
            <span className="text-[10px] font-semibold text-slate-500 block">Current Speed</span>
            <div className="text-base font-extrabold text-slate-900 dark:text-white mt-1">
              {currentSpeed} <span className="text-[11px] font-normal text-slate-400">km/h</span>
            </div>
          </div>

          {/* Free-flow Speed */}
          <div className="bg-slate-50 dark:bg-slate-900/50 p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800">
            <span className="text-[10px] font-semibold text-slate-500 block">Free-flow Speed</span>
            <div className="text-base font-extrabold text-slate-900 dark:text-white mt-1">
              {freeFlowSpeed} <span className="text-[11px] font-normal text-slate-400">km/h</span>
            </div>
          </div>

          {/* Traffic Condition */}
          <div className="bg-amber-50/50 dark:bg-amber-950/20 p-2.5 rounded-xl border border-amber-200/60 dark:border-amber-900/40 flex flex-col justify-between">
            <span className="text-[10px] font-bold text-amber-600 dark:text-amber-400">Traffic Condition</span>
            <div className="text-sm font-extrabold text-amber-600 dark:text-amber-400 mt-1">
              {condition}
            </div>
          </div>
        </div>
      </div>

      {/* Sidebar Footer */}
      <div className="flex items-center justify-between text-[11px] font-medium text-slate-400 dark:text-slate-500 px-1">
        <span>Last Updated: {currentTimeStr}</span>
        <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400 font-semibold">
          <RefreshCw className="w-3 h-3 animate-spin" />
          <span>Auto Refresh: ON</span>
        </span>
      </div>
    </div>
  );
};
