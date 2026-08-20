import { AlertTriangle, Map, Clock, Zap, Activity, Loader2, Eye, Check } from "lucide-react";
import { useNavigationEngineContext } from "../../navigation-engine/context/NavigationEngineContext";

export const RerouteNotification = () => {
  const { 
    rerouteRecommendation, 
    previewRoute,
    setPreviewRoute,
    acceptReroute, 
    rejectReroute,
    isRouteSwitching,
    routeSwitchError
  } = useNavigationEngineContext();

  if (!rerouteRecommendation) return null;
  const validStatuses = ["REROUTE_AVAILABLE", "NO_BETTER_ROUTE", "CALCULATING"];
  if (!validStatuses.includes(rerouteRecommendation.status)) return null;

  const { reason, current_route, alternative_route, alternative_routes } = rerouteRecommendation;

  const candidates = alternative_routes && alternative_routes.length > 0
    ? alternative_routes
    : (alternative_route ? [alternative_route] : []);

  const selectedCandidate = previewRoute || candidates[0];

  const currentLevel = current_route?.traffic_level || "MEDIUM";

  return (
    <div className="bg-amber-50/90 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-500/40 rounded-xl p-4 flex flex-col gap-3 shadow-lg animate-in fade-in slide-in-from-top-2 duration-300">
      
      {/* Header Alert Banner */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className={`p-2 rounded-lg shrink-0 ${currentLevel === 'HIGH' ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400 animate-pulse' : 'bg-amber-500/20 text-amber-600 dark:text-amber-400'}`}>
            <AlertTriangle size={18} />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-100">
                TRAFFIC ALERT
              </h4>
              <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                currentLevel === 'HIGH' ? 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300 border border-rose-300' :
                currentLevel === 'MEDIUM' ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 border border-amber-300' :
                'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 border border-emerald-300'
              }`}>
                {currentLevel} TRAFFIC
              </span>
            </div>
            <p className="text-xs text-slate-700 dark:text-slate-300 mt-1 leading-snug">
              {reason}
            </p>
          </div>
        </div>
      </div>

      {/* Route Cards Container */}
      <div className="flex flex-col gap-2 mt-1">
        
        {/* Active Current Route Summary Card */}
        {current_route && (
          <div className="bg-white/80 dark:bg-black/40 rounded-lg p-2.5 border border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping shrink-0" />
              <span className="font-semibold text-slate-700 dark:text-slate-300">Active Route:</span>
              <span className="text-slate-600 dark:text-slate-400">{current_route.distance_km} km · ~{current_route.eta_minutes} min</span>
            </div>
            <span className="font-mono text-[10px] text-slate-500">Cost: {current_route.traffic_cost || 0}</span>
          </div>
        )}

        {/* Searching for Better Routes Loading Card */}
        {rerouteRecommendation.status === "CALCULATING" && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 flex items-center gap-3 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
            <Loader2 className="animate-spin text-emerald-600 shrink-0" size={18} />
            <div className="flex flex-col">
              <span>Searching for 2–3 diverse alternative routes...</span>
              <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400">Evaluating A* & Dijkstra paths in parallel (under 30s)</span>
            </div>
          </div>
        )}

        {/* Candidate Alternatives List (Up to 3) */}
        {candidates.length > 0 && (
          <div className="grid grid-cols-1 gap-2">
            {candidates.map((cand, idx) => {
              const isSelected = selectedCandidate && selectedCandidate.id === cand.id;
              const candColor = cand.color || (idx === 0 ? '#22c55e' : idx === 1 ? '#06b6d4' : '#a855f7');
              const label = cand.label || (idx === 0 ? 'Recommended' : `Alternative ${idx + 1}`);

              return (
                <div 
                  key={cand.id || `cand_card_${idx}`}
                  onClick={() => setPreviewRoute(cand)}
                  className={`cursor-pointer rounded-lg p-3 border transition-all duration-200 flex items-center justify-between ${
                    isSelected 
                      ? 'bg-emerald-500/10 border-emerald-500 ring-2 ring-emerald-500/30 shadow-md' 
                      : 'bg-white/60 dark:bg-slate-900/60 border-slate-200 dark:border-slate-800 hover:border-emerald-400/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-3.5 h-3.5 rounded-full shrink-0 flex items-center justify-center" style={{ backgroundColor: candColor }}>
                      {isSelected && <Check size={10} className="text-white stroke-[3]" />}
                    </div>

                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-100">{label}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 uppercase">
                          {cand.algorithm === 'astar' ? 'A*' : 'Dijkstra'}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                        <span className="flex items-center gap-1"><Map size={11} /> {cand.distance_km} km</span>
                        <span className="flex items-center gap-1"><Clock size={11} /> ~{cand.eta_minutes} min</span>
                        <span className="flex items-center gap-1 font-mono text-[10px]"><Activity size={10} /> Cost: {cand.traffic_cost}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1 shrink-0">
                    {cand.improvement_percent ? (
                      <span className="bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-300 text-[10px] font-extrabold px-2 py-0.5 rounded-full">
                        {cand.improvement_percent}% FASTER
                      </span>
                    ) : null}

                    <span className="text-[10px] text-slate-400 flex items-center gap-1">
                      <Eye size={10} /> {isSelected ? "Previewing" : "Click to Preview"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {isRouteSwitching ? (
        <div className="flex items-center justify-center gap-2 py-2 mt-1 text-xs font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg border border-emerald-200 dark:border-emerald-500/30">
          <Loader2 className="animate-spin" size={14} />
          <span>Switching to Selected Route...</span>
        </div>
      ) : candidates.length > 0 ? (
        <div className="flex gap-2 mt-1">
          <button 
            onClick={() => acceptReroute(selectedCandidate)}
            disabled={isRouteSwitching}
            className="flex-1 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold py-2.5 px-3 rounded-lg shadow transition-colors flex items-center justify-center gap-1.5"
          >
            <Check size={14} />
            Use This Route ({selectedCandidate?.label || 'Selected'})
          </button>
          <button 
            onClick={rejectReroute}
            disabled={isRouteSwitching}
            className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold py-2.5 px-3 rounded-lg transition-colors"
          >
            Keep Current
          </button>
        </div>
      ) : (
        <div className="flex gap-2 mt-1">
          <button 
            onClick={rejectReroute}
            disabled={isRouteSwitching}
            className="flex-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold py-2.5 px-3 rounded-lg transition-colors"
          >
            Dismiss
          </button>
        </div>
      )}

      {routeSwitchError && (
        <div className="text-[11px] font-semibold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/40 rounded-lg p-2 mt-1">
          {routeSwitchError}
        </div>
      )}

    </div>
  );
};
