import { GitFork, Loader2, AlertCircle, CheckCircle, RefreshCw, Activity } from "lucide-react";
import { InfoCard } from "./InfoCard";
import { useNavigationEngineContext } from "../../navigation-engine/context/NavigationEngineContext";

const trafficBadge = (level) => {
  if (level === "HIGH")   return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
  if (level === "MEDIUM") return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
  return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
};

export const AlternativeRoutesCard = () => {
  const {
    activeRoute,
    vehicles,
    simulationStatus,
    alternativeRoutes,
    isGeneratingAlternatives,
    alternativeGenerationError,
    alternativeAnalysisStatus,
    handleGenerateAlternatives,
  } = useNavigationEngineContext();

  // ── Don't render unless we have an active route ───────────────────────────
  if (!activeRoute) return null;

  const hasVehicles = vehicles && vehicles.length > 0;
  const hasResults  = alternativeRoutes && alternativeRoutes.length > 0;
  const isSimRunning = simulationStatus === "running";
  const isSimIdle    = simulationStatus === "idle";

  // Button should be enabled when: simulation is running, analysis is done (or error/idle with sim running), and not currently generating
  const canManualGenerate = isSimRunning && !isGeneratingAlternatives && alternativeAnalysisStatus !== "waiting";

  // Derived status badge for card header
  const getStatusBadge = () => {
    if (isGeneratingAlternatives || alternativeAnalysisStatus === "analyzing") {
      return (
        <span className="text-xs font-semibold text-amber-500 flex items-center gap-1">
          <Loader2 size={12} className="animate-spin" /> Analyzing
        </span>
      );
    }
    if (hasResults) {
      return (
        <span className="text-xs font-semibold text-emerald-500 flex items-center gap-1">
          <CheckCircle size={12} /> {alternativeRoutes.length} found
        </span>
      );
    }
    if (alternativeAnalysisStatus === "waiting") {
      return (
        <span className="text-xs font-semibold text-blue-500 flex items-center gap-1">
          <Activity size={12} className="animate-pulse" /> Preparing
        </span>
      );
    }
    return null;
  };

  return (
    <InfoCard
      title="Alternative Routes"
      icon={GitFork}
      subtitle="Find better routes using A* & Dijkstra"
      status={getStatusBadge()}
    >
      <div className="space-y-4">

        {/* ── Status Row ─────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500 dark:text-slate-400 font-medium">Status</span>
          <span className="font-semibold text-slate-800 dark:text-white">
            {isGeneratingAlternatives || alternativeAnalysisStatus === "analyzing" ? (
              <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
                <Loader2 size={13} className="animate-spin" /> Finding alternatives...
              </span>
            ) : hasResults ? (
              <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                <CheckCircle size={13} /> {alternativeRoutes.length} route{alternativeRoutes.length > 1 ? "s" : ""} found
              </span>
            ) : alternativeAnalysisStatus === "waiting" ? (
              <span className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400">
                <Activity size={13} className="animate-pulse" /> Analyzing traffic...
              </span>
            ) : alternativeGenerationError ? (
              <span className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400">
                <AlertCircle size={13} /> Analysis complete
              </span>
            ) : isSimRunning ? (
              <span className="text-slate-500 dark:text-slate-400">Simulation active</span>
            ) : hasVehicles ? (
              <span className="text-slate-500 dark:text-slate-400">Waiting for simulation...</span>
            ) : (
              <span className="text-slate-500 dark:text-slate-400">Waiting for simulation...</span>
            )}
          </span>
        </div>

        {/* ── Waiting / Preparing animation ───────────────────────────── */}
        {alternativeAnalysisStatus === "waiting" && !isGeneratingAlternatives && (
          <div className="flex flex-col items-center justify-center py-4 gap-2 bg-blue-50 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900/40 rounded-xl">
            <Activity size={20} className="text-blue-500 animate-pulse" />
            <p className="text-xs font-semibold text-blue-700 dark:text-blue-400">Analyzing traffic patterns...</p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Alternative route analysis will begin shortly</p>
            <div className="flex gap-1 mt-1">
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-1.5 w-5 rounded-full bg-blue-400 dark:bg-blue-500 animate-pulse"
                  style={{ animationDelay: `${i * 200}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {/* ── Pre-simulation waiting ─────────────────────────────────── */}
        {!isSimRunning && !hasResults && !isGeneratingAlternatives && alternativeAnalysisStatus === "idle" && (
          <div className="text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 rounded-xl p-3 text-center">
            {hasVehicles
              ? "Start the simulation to begin alternative route analysis."
              : "Generate vehicles and start simulation to analyze alternative routes."
            }
          </div>
        )}

        {/* ── Generating Routes loading state ───────────────────────────── */}
        {(isGeneratingAlternatives || alternativeAnalysisStatus === "analyzing") && alternativeAnalysisStatus !== "waiting" && (
          <div className="flex flex-col items-center gap-2 py-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-100 dark:border-amber-900/40 rounded-xl">
            <Loader2 size={22} className="animate-spin text-amber-500" />
            <p className="text-xs font-semibold text-amber-700 dark:text-amber-400">Generating Routes...</p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 animate-pulse">Finding best alternatives via A* & Dijkstra</p>
          </div>
        )}

        {/* ── Error / Timeout Message ────────────────────────────────────── */}
        {alternativeGenerationError && !isGeneratingAlternatives && (
          <div className="flex items-start gap-2 text-xs text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800/40 rounded-xl p-3">
            <AlertCircle size={13} className="mt-0.5 shrink-0" />
            <span>{alternativeGenerationError}</span>
          </div>
        )}

        {/* ── Results Panel ──────────────────────────────────────────────── */}
        {!isGeneratingAlternatives && hasResults && (
          <div className="space-y-2.5">
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span>{alternativeRoutes.length} Route{alternativeRoutes.length > 1 ? "s" : ""} Found</span>
              <CheckCircle size={12} className="text-emerald-500" />
            </div>

            {/* Alternative Route Cards */}
            {alternativeRoutes.map((alt, idx) => {
              const altColor = alt.color || (idx === 0 ? "#22c55e" : "#3b82f6");
              const altLabel = alt.label || `Alternative ${idx + 1}`;
              const distKm   = (alt.distance_km || alt.total_distance_km || 0).toFixed(1);
              const etaMin   = alt.eta_minutes || Math.round((alt.travel_time_seconds || alt.total_travel_time_seconds || 0) / 60);
              const tLevel   = alt.traffic_level || "LOW";
              const algo     = alt.algorithm || "A*";

              return (
                <div
                  key={alt.id || idx}
                  className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm"
                  style={{ borderLeftWidth: 3, borderLeftColor: altColor }}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="flex items-center gap-1.5 font-bold text-xs" style={{ color: altColor }}>
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: altColor }} />
                      {altLabel}
                    </span>
                    <span className="text-slate-500 dark:text-slate-400 text-[11px] font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                      {algo}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-700 dark:text-slate-300">
                    <span className="font-semibold">{distKm} km &bull; {etaMin} min</span>
                    <span className={`px-1.5 py-0.5 rounded-md text-[10px] font-bold ${trafficBadge(tLevel)}`}>
                      {tLevel}
                    </span>
                  </div>
                </div>
              );
            })}

            {/* Current Route Baseline */}
            {activeRoute && (
              <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/40"
                   style={{ borderLeftWidth: 3, borderLeftColor: "#ef4444" }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="flex items-center gap-1.5 font-bold text-xs text-red-600 dark:text-red-400">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                    Current Route
                  </span>
                  <span className="text-red-500 dark:text-red-400 text-[11px] font-mono bg-red-100 dark:bg-red-900/30 px-1.5 py-0.5 rounded">
                    ACTIVE
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-red-700 dark:text-red-300">
                  <span className="font-semibold">
                    {((activeRoute.total_distance_km ?? activeRoute.distance_km) || 0).toFixed(1)} km &bull;&nbsp;
                    {Math.max(1, Math.round((activeRoute.total_travel_time_seconds ?? 0) / 60))} min
                  </span>
                  <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300">
                    {activeRoute.traffic_level || "N/A"}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Generate Routes Button ─────────────────────────────────────── */}
        <button
          id="btn-generate-alternative-routes"
          onClick={handleGenerateAlternatives}
          disabled={!canManualGenerate}
          className={`w-full py-2.5 px-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all duration-200 shadow-sm ${
            canManualGenerate
              ? "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white cursor-pointer shadow-md hover:shadow-lg"
              : "bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-600 cursor-not-allowed"
          }`}
        >
          {isGeneratingAlternatives ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              Generating Routes...
            </>
          ) : (
            <>
              <GitFork size={15} />
              Generate Routes
            </>
          )}
        </button>

        {/* Re-generate button when results already exist */}
        {canManualGenerate && hasResults && (
          <button
            onClick={handleGenerateAlternatives}
            className="w-full py-1.5 px-3 rounded-lg text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 flex items-center justify-center gap-1.5 transition-colors border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600"
          >
            <RefreshCw size={12} /> Re-generate
          </button>
        )}

      </div>
    </InfoCard>
  );
};
