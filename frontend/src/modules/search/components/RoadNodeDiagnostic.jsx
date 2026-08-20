import { useNavigationEngineContext } from "../../navigation-engine/context/NavigationEngineContext";
import { Activity, MapPin, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";

/**
 * RoadNodeDiagnostic — Sprint 5.4
 *
 * Development-only diagnostic panel displaying current Source and Destination
 * Road Network Node IDs, nearest-node distance, and lookup status.
 */
export const RoadNodeDiagnostic = () => {
  const {
    sourceRoadNode,
    destinationRoadNode,
    sourceNodeLoading,
    destinationNodeLoading,
    sourceNodeError,
    destinationNodeError,
    sourceLocation,
    destinationLocation,
    isDebugMode,
    setIsDebugMode,
  } = useNavigationEngineContext();

  if (!isDebugMode) {
    return (
      <button
        onClick={() => setIsDebugMode(true)}
        className="text-[10px] text-slate-400 dark:text-slate-500 hover:text-primary underline flex items-center gap-1 transition-colors px-1 py-0.5"
      >
        <Activity size={10} /> Inspect Road Nodes (Dev)
      </button>
    );
  }

  const formatDist = (km) => {
    if (km == null) return "N/A";
    if (km < 1) {
      return `${Math.round(km * 1000)} m`;
    }
    return `${km.toFixed(2)} km`;
  };

  return (
    <div className="mt-2 p-3 bg-slate-900/95 dark:bg-slate-950/95 text-slate-100 rounded-xl border border-slate-700/80 shadow-xl text-xs space-y-2 animate-fade-in font-mono">
      <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
        <div className="flex items-center gap-1.5 font-sans font-bold text-amber-400 text-xs">
          <Activity size={13} /> Road Network Diagnostics
        </div>
        <button
          onClick={() => setIsDebugMode(false)}
          className="text-[10px] text-slate-400 hover:text-white font-sans px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700"
        >
          Hide
        </button>
      </div>

      {/* Source Node */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-emerald-400 font-sans font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Source Node:
          </span>
          {sourceNodeLoading ? (
            <span className="text-amber-300 flex items-center gap-1">
              <Loader2 size={11} className="animate-spin" /> Resolving...
            </span>
          ) : sourceRoadNode ? (
            <span className="text-emerald-300 font-bold flex items-center gap-1">
              <CheckCircle2 size={11} /> Ready
            </span>
          ) : sourceNodeError ? (
            <span className="text-rose-400 flex items-center gap-1" title={sourceNodeError}>
              <AlertTriangle size={11} /> Outside Coverage
            </span>
          ) : sourceLocation ? (
            <span className="text-slate-400">Waiting</span>
          ) : (
            <span className="text-slate-500">None selected</span>
          )}
        </div>

        {sourceRoadNode && (
          <div className="pl-2 border-l border-emerald-500/30 text-[10px] text-slate-300 space-y-0.5">
            <div><span className="text-slate-400">ID:</span> <span className="text-emerald-200 font-bold">{sourceRoadNode.nodeId}</span></div>
            <div><span className="text-slate-400">Snap Dist:</span> {formatDist(sourceRoadNode.distance)}</div>
            <div><span className="text-slate-400">Coords:</span> {sourceRoadNode.latitude.toFixed(5)}, {sourceRoadNode.longitude.toFixed(5)}</div>
          </div>
        )}

        {sourceNodeError && (
          <div className="text-[10px] text-rose-300 pl-2 border-l border-rose-500/30">
            {sourceNodeError}
          </div>
        )}
      </div>

      {/* Destination Node */}
      <div className="space-y-1 pt-1.5 border-t border-slate-800/60">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-rose-400 font-sans font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Dest Node:
          </span>
          {destinationNodeLoading ? (
            <span className="text-amber-300 flex items-center gap-1">
              <Loader2 size={11} className="animate-spin" /> Resolving...
            </span>
          ) : destinationRoadNode ? (
            <span className="text-emerald-300 font-bold flex items-center gap-1">
              <CheckCircle2 size={11} /> Ready
            </span>
          ) : destinationNodeError ? (
            <span className="text-rose-400 flex items-center gap-1" title={destinationNodeError}>
              <AlertTriangle size={11} /> Outside Coverage
            </span>
          ) : destinationLocation ? (
            <span className="text-slate-400">Waiting</span>
          ) : (
            <span className="text-slate-500">None selected</span>
          )}
        </div>

        {destinationRoadNode && (
          <div className="pl-2 border-l border-rose-500/30 text-[10px] text-slate-300 space-y-0.5">
            <div><span className="text-slate-400">ID:</span> <span className="text-rose-200 font-bold">{destinationRoadNode.nodeId}</span></div>
            <div><span className="text-slate-400">Snap Dist:</span> {formatDist(destinationRoadNode.distance)}</div>
            <div><span className="text-slate-400">Coords:</span> {destinationRoadNode.latitude.toFixed(5)}, {destinationRoadNode.longitude.toFixed(5)}</div>
          </div>
        )}

        {destinationNodeError && (
          <div className="text-[10px] text-rose-300 pl-2 border-l border-rose-500/30">
            {destinationNodeError}
          </div>
        )}
      </div>
    </div>
  );
};
