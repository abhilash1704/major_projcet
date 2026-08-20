import { GitCompare, Clock, Ruler, Network, Zap, CheckCircle2, Activity } from "lucide-react";
import { InfoCard } from "./InfoCard";
import { useNavigationEngineContext } from "../../navigation-engine/context/NavigationEngineContext";

export const RouteComparisonCard = () => {
  const { comparisonData, routeLoading } = useNavigationEngineContext();

  if (routeLoading || !comparisonData || !comparisonData.comparison) {
    return null; // Do not show when loading or when no comparison data exists
  }

  const { astar, dijkstra } = comparisonData.comparison;
  const recommendation = comparisonData.recommendation;

  const astarSuccess = Boolean(astar?.success);
  const dijkstraSuccess = Boolean(dijkstra?.success);

  if (!astarSuccess && !dijkstraSuccess) {
    return (
      <InfoCard title="Engine Comparison" icon={GitCompare} subtitle="A* vs Dijkstra">
        <div className="text-xs font-medium text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/40 rounded-lg p-3">
          No route available. Both algorithms failed to find a valid road path.
        </div>
      </InfoCard>
    );
  }

  const formatVal = (res, key, unit = "", isNumber = true) => {
    if (!res || !res.success) return "Unavailable";
    const val = res[key];
    if (val === undefined || val === null || (isNumber && Number.isNaN(val))) {
      return "Unavailable";
    }
    if (typeof val === "number") {
      return unit ? `${val.toLocaleString()} ${unit}` : val.toLocaleString();
    }
    return unit ? `${val} ${unit}` : String(val);
  };

  return (
    <InfoCard title="Engine Comparison" icon={GitCompare} subtitle="A* vs Dijkstra">
      <div className="flex flex-col gap-3">
        {/* Recommendation Banner */}
        {recommendation && recommendation.algorithm !== "none" && (
          <div className="px-3 py-2 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 rounded-lg flex items-start gap-2">
            <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
            <div className="flex flex-col">
              <span className="text-sm font-medium text-emerald-800 dark:text-emerald-300 leading-tight">
                Recommended: {recommendation.algorithm === "astar" ? "A* Search" : "Dijkstra"}
              </span>
              <span className="text-xs text-emerald-700 dark:text-emerald-400/80 mt-1">
                {recommendation.reason}
              </span>
            </div>
          </div>
        )}

        {/* Comparison Table */}
        <div className="grid grid-cols-3 text-xs gap-1">
          {/* Headers */}
          <div className="font-semibold text-slate-500 dark:text-slate-400 pb-1 border-b border-slate-100 dark:border-slate-800">Metric</div>
          <div className={`font-semibold pb-1 border-b border-slate-100 dark:border-slate-800 ${recommendation?.algorithm === 'astar' ? 'text-primary' : 'text-slate-500 dark:text-slate-400'}`}>A* Search</div>
          <div className={`font-semibold pb-1 border-b border-slate-100 dark:border-slate-800 ${recommendation?.algorithm === 'dijkstra' ? 'text-primary' : 'text-slate-500 dark:text-slate-400'}`}>Dijkstra</div>

          {/* Execution Time */}
          <div className="py-1.5 text-slate-500 flex items-center gap-1"><Zap size={12}/> Time</div>
          <div className="py-1.5 text-slate-700 dark:text-slate-300 font-medium">
            {formatVal(astar, 'execution_time_ms', 'ms')}
          </div>
          <div className="py-1.5 text-slate-700 dark:text-slate-300 font-medium">
            {formatVal(dijkstra, 'execution_time_ms', 'ms')}
          </div>

          {/* Nodes Explored */}
          <div className="py-1.5 text-slate-500 flex items-center gap-1"><Network size={12}/> Explored</div>
          <div className="py-1.5 text-slate-700 dark:text-slate-300">
            {formatVal(astar, 'nodes_explored')}
          </div>
          <div className="py-1.5 text-slate-700 dark:text-slate-300">
            {formatVal(dijkstra, 'nodes_explored')}
          </div>

          {/* ETA */}
          <div className="py-1.5 text-slate-500 flex items-center gap-1"><Clock size={12}/> ETA</div>
          <div className="py-1.5 text-slate-700 dark:text-slate-300">
            {formatVal(astar, 'eta_minutes', 'min')}
          </div>
          <div className="py-1.5 text-slate-700 dark:text-slate-300">
            {formatVal(dijkstra, 'eta_minutes', 'min')}
          </div>

          {/* Distance */}
          <div className="py-1.5 text-slate-500 flex items-center gap-1"><Ruler size={12}/> Distance</div>
          <div className="py-1.5 text-slate-700 dark:text-slate-300">
            {formatVal(astar, 'distance_km', 'km')}
          </div>
          <div className="py-1.5 text-slate-700 dark:text-slate-300">
            {formatVal(dijkstra, 'distance_km', 'km')}
          </div>

          {/* Traffic Cost */}
          <div className="py-1.5 text-slate-500 flex items-center gap-1"><Activity size={12}/> Traffic Cost</div>
          <div className="py-1.5 text-slate-700 dark:text-slate-300">
            {formatVal(astar, 'total_cost')}
          </div>
          <div className="py-1.5 text-slate-700 dark:text-slate-300">
            {formatVal(dijkstra, 'total_cost')}
          </div>
        </div>
      </div>
    </InfoCard>
  );
};
