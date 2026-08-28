/**
 * BottomMetricsBar.jsx — Low-Prominence System Health & Operational Status Bar
 *
 * Keeps system health indicators present at the bottom of the viewport with low visual prominence.
 */
export const BottomMetricsBar = () => {
  return (
    <div className="w-full bg-slate-100/90 dark:bg-slate-900/90 border-t border-slate-200 dark:border-slate-800 px-4 py-2 flex items-center justify-between text-[11px] font-medium text-slate-500 dark:text-slate-400 shrink-0">
      
      {/* System Health Indicators */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-1.5">
          <span className="text-slate-400 dark:text-slate-500">Backend</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-semibold text-slate-700 dark:text-slate-300">Connected</span>
        </div>

        <span className="text-slate-300 dark:text-slate-700">•</span>

        <div className="flex items-center gap-1.5">
          <span className="text-slate-400 dark:text-slate-500">Frontend</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-semibold text-slate-700 dark:text-slate-300">Connected</span>
        </div>

        <span className="text-slate-300 dark:text-slate-700">•</span>

        <div className="flex items-center gap-1.5">
          <span className="text-slate-400 dark:text-slate-500">Database</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-semibold text-slate-700 dark:text-slate-300">Connected</span>
        </div>

        <span className="text-slate-300 dark:text-slate-700 hidden sm:inline">•</span>

        <div className="hidden sm:flex items-center gap-1.5">
          <span className="text-slate-400 dark:text-slate-500">DBSCAN Engine</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-semibold text-slate-700 dark:text-slate-300">Operational</span>
        </div>
      </div>

      {/* Cycle / Window Status */}
      <div className="flex items-center gap-3">
        <span className="hidden md:inline text-slate-400">Rolling Window: <strong className="font-semibold text-slate-700 dark:text-slate-300">5s</strong></span>
        <span className="bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 px-2 py-0.5 rounded font-mono text-[10px] font-bold">
          20s Cycle
        </span>
      </div>

    </div>
  );
};
