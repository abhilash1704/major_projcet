import { Route, Navigation, CheckCircle, Loader2, AlertCircle, Clock, Ruler } from "lucide-react";
import { InfoCard } from "./InfoCard";
import { useNavigationEngineContext } from "../../navigation-engine/context/NavigationEngineContext";

export const RouteCard = () => {
  const { activeRoute, routeLoading, routeError, selectedAlgorithm } = useNavigationEngineContext();

  // ── Loading state ──────────────────────────────────────────────────────
  if (routeLoading) {
    const loadingAlgoLabel = selectedAlgorithm === "dijkstra" ? "Dijkstra" : "A* Search";
    return (
      <InfoCard title="Route Summary" icon={Route} subtitle="Calculating…">
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <Loader2 size={14} className="animate-spin text-primary" />
          <span>Running {loadingAlgoLabel}…</span>
        </div>
      </InfoCard>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────
  if (routeError && !activeRoute) {
    return (
      <InfoCard title="Route Summary" icon={Route} subtitle="Optimal Navigation Path">
        <div className="flex items-start gap-2 text-xs text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800/40 rounded-xl px-3 py-2">
          <AlertCircle size={13} className="mt-0.5 shrink-0" />
          <span>{routeError}</span>
        </div>
      </InfoCard>
    );
  }

  // ── Active route ───────────────────────────────────────────────────────
  if (activeRoute) {
    const distKm  = activeRoute.total_distance_km ?? activeRoute.distance_km ?? 0;
    const etaSec  = activeRoute.total_travel_time_seconds ?? activeRoute.travel_time_seconds ?? 0;
    const etaMins = Math.max(1, Math.round(etaSec / 60));
    const nodeCount = activeRoute.nodes?.length ?? 0;
    const rawAlgo = String(activeRoute.algorithm || "").toLowerCase();
    const algoLabel = rawAlgo === "dijkstra" ? "Dijkstra" : "A* Search";
    const mode = activeRoute.routing_mode || "normal";
    const isTrafficAware = mode === "traffic_aware";
    const baseCostSec = activeRoute.base_cost ?? activeRoute.base_travel_time_seconds ?? etaSec;
    const trafficCostSec = activeRoute.traffic_cost ?? activeRoute.traffic_penalty_seconds ?? 0;
    const trafficLevel = activeRoute.traffic_level || (isTrafficAware && trafficCostSec > 0 ? "MEDIUM" : "LOW");

    return (
      <InfoCard title="Route Summary" icon={Route} subtitle="Optimal Navigation Path">
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Status</span>
            <span className="flex items-center gap-1.5 font-semibold text-emerald-600 dark:text-emerald-400">
              <CheckCircle size={13} />
              Route Ready
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 font-medium">
              <Ruler size={12} />
              Distance
            </span>
            <span className="font-semibold text-slate-900 dark:text-white">
              {distKm.toFixed(2)} km
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 font-medium">
              <Clock size={12} />
              ETA
            </span>
            <span className="font-semibold text-slate-900 dark:text-white">
              {etaMins} min ({Math.round(etaSec)}s)
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Algorithm</span>
            <span className="font-semibold text-primary text-xs tracking-wide">{algoLabel}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Routing Mode</span>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
              isTrafficAware
                ? "bg-amber-500/10 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400"
                : "bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400"
            }`}>
              {isTrafficAware ? "TRAFFIC-AWARE" : "NORMAL"}
            </span>
          </div>

          {/* Traffic Delay Breakdown if Traffic-Aware */}
          {isTrafficAware && (
            <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/60 space-y-1.5 text-xs">
              <div className="flex justify-between text-slate-500 dark:text-slate-400">
                <span>Base Travel Time:</span>
                <span className="font-mono text-slate-700 dark:text-slate-300">{baseCostSec.toFixed(1)}s</span>
              </div>
              <div className="flex justify-between text-slate-500 dark:text-slate-400">
                <span>Traffic Penalty:</span>
                <span className={`font-mono font-semibold ${trafficCostSec > 0 ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                  +{trafficCostSec.toFixed(1)}s
                </span>
              </div>
              <div className="flex justify-between items-center pt-1 border-t border-slate-200 dark:border-slate-700">
                <span className="font-medium text-slate-700 dark:text-slate-200">Traffic Level:</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-extrabold ${
                  trafficLevel === "HIGH" ? "bg-rose-500/20 text-rose-600" :
                  trafficLevel === "MEDIUM" ? "bg-amber-500/20 text-amber-600" : "bg-emerald-500/20 text-emerald-600"
                }`}>
                  {trafficLevel}
                </span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Route Status</span>
            <span className="flex items-center gap-1 text-xs font-bold text-emerald-600 dark:text-emerald-400 tracking-wider">
              <CheckCircle size={11} />
              READY
            </span>
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400 dark:text-slate-500">
            <span>Nodes</span>
            <span className="font-mono">{nodeCount}</span>
          </div>
        </div>
      </InfoCard>
    );
  }

  // ── Default / no route ─────────────────────────────────────────────────
  return (
    <InfoCard title="Route Summary" icon={Route} subtitle="Optimal Navigation Path">
      <div className="space-y-3.5 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-slate-500 dark:text-slate-400 font-medium">Status</span>
          <span className="font-semibold text-slate-900 dark:text-white">Pending Selection</span>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
          <span className="text-slate-500 dark:text-slate-400 font-medium">Route Status</span>
          <span className="flex items-center gap-1 text-xs font-bold text-amber-600 tracking-wider">
            READY FOR ROUTING
          </span>
        </div>
      </div>
    </InfoCard>
  );
};
