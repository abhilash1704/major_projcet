/**
 * BottomMetricsBar.jsx — Low-Prominence System Health & Operational Status Bar
 *
 * Displays compact live status indicators with optional system detail drawer.
 */
import { useState } from "react";
import { Activity, Server, ChevronUp, ChevronDown } from "lucide-react";

export const BottomMetricsBar = () => {
  const [showSysDetails, setShowSysDetails] = useState(false);

  return (
    <div className="w-full bg-slate-100/90 dark:bg-slate-900/90 border-t border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400 shrink-0 font-sans">
      
      {/* Primary Compact Status Bar */}
      <div className="px-4 py-2 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3.5 flex-wrap">
          <div className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>System Online</span>
          </div>

          <span className="text-slate-300 dark:text-slate-700">•</span>

          <div className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-300">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span>Clustering Active</span>
          </div>

          <span className="text-slate-300 dark:text-slate-700">•</span>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 dark:text-slate-500">Auto Update:</span>
            <strong className="font-semibold text-slate-700 dark:text-slate-300">20s</strong>
          </div>

          <span className="text-slate-300 dark:text-slate-700">•</span>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 dark:text-slate-500">Last update:</span>
            <strong className="font-semibold text-emerald-600 dark:text-emerald-400">just now</strong>
          </div>
        </div>

        {/* Expandable System Details Button */}
        <button
          onClick={() => setShowSysDetails(!showSysDetails)}
          className="flex items-center gap-1 text-[10px] font-bold text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition cursor-pointer"
        >
          <Server className="w-3 h-3 text-slate-400" />
          <span>System Details</span>
          {showSysDetails ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
        </button>
      </div>

      {/* Expandable System Details Panel */}
      {showSysDetails && (
        <div className="px-4 py-2 bg-slate-200/60 dark:bg-slate-800/80 border-t border-slate-200/80 dark:border-slate-800 text-[10px] grid grid-cols-2 sm:grid-cols-4 gap-2 text-slate-600 dark:text-slate-300">
          <div>Backend API: <strong className="text-emerald-600 dark:text-emerald-400 font-bold">Connected</strong></div>
          <div>DBSCAN Engine: <strong className="text-emerald-600 dark:text-emerald-400 font-bold">Operational</strong></div>
          <div>Graph Service: <strong className="text-emerald-600 dark:text-emerald-400 font-bold">Read-Only</strong></div>
          <div>Spatial Filter: <strong className="text-blue-600 dark:text-blue-400 font-bold">Haversine 2-Stage</strong></div>
        </div>
      )}

    </div>
  );
};
