/**
 * TrajectoryReplayPanel.jsx — Synthetic Vehicle Trajectory Generator & Replay Controls
 */
import { useState } from "react";
import { useLiveClustering } from "../context/LiveClusteringContext";
import { Play, Pause, Square, RefreshCw, Zap, Users, Gauge } from "lucide-react";

export const TrajectoryReplayPanel = () => {
  const {
    replayState,
    generateTrajectories,
    startReplay,
    pauseReplay,
    stopReplay,
    setReplaySpeed,
    status,
  } = useLiveClustering();

  const [numVehicles, setNumVehicles]           = useState(15);
  const [multiUserRatio, setMultiUserRatio]   = useState(0.5);
  const [durationMinutes, setDurationMinutes] = useState(5);
  const [isGenerating, setIsGenerating]       = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    await generateTrajectories({
      num_vehicles: Number(numVehicles),
      multi_user_ratio: Number(multiUserRatio),
      duration_minutes: Number(durationMinutes),
    });
    setIsGenerating(false);
  };

  const isRunning = replayState.status === "RUNNING";
  const isPaused  = replayState.status === "PAUSED";
  const isReady   = replayState.status === "READY" || isPaused || isRunning;

  return (
    <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Trajectory Replay Engine</h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Clock-Driven Road-Constrained Replay</p>
          </div>
        </div>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
          replayState.status === "RUNNING"
            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-300 animate-pulse"
            : replayState.status === "PAUSED"
              ? "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border-amber-300"
              : replayState.status === "READY"
                ? "bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-300"
                : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border-slate-300"
        }`}>
          {replayState.status}
        </span>
      </div>

      {/* Control Buttons & Speed */}
      <div className="flex items-center justify-between gap-2 bg-slate-50 dark:bg-slate-900/60 p-2 rounded-lg border border-slate-200/60 dark:border-slate-800">
        <div className="flex items-center gap-1.5">
          {!isRunning ? (
            <button
              onClick={startReplay}
              disabled={!isReady}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-medium text-xs rounded-md shadow-sm transition flex items-center gap-1"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Start</span>
            </button>
          ) : (
            <button
              onClick={pauseReplay}
              className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs rounded-md shadow-sm transition flex items-center gap-1"
            >
              <Pause className="w-3.5 h-3.5 fill-current" />
              <span>Pause</span>
            </button>
          )}

          <button
            onClick={stopReplay}
            disabled={!isReady && replayState.status === "IDLE"}
            className="px-2.5 py-1.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs rounded-md transition flex items-center gap-1"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>Stop</span>
          </button>
        </div>

        {/* Speed Selector */}
        <div className="flex items-center gap-1 bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-800 p-0.5 rounded-md">
          {[1.0, 5.0, 10.0].map((s) => (
            <button
              key={s}
              onClick={() => setReplaySpeed(s)}
              className={`px-2 py-0.5 text-[11px] font-medium rounded ${
                replayState.speed === s
                  ? "bg-indigo-600 text-white shadow-xs"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Frame Counter Progress Bar */}
      {replayState.total_frames > 0 && (
        <div className="flex flex-col gap-1">
          <div className="flex justify-between text-[10px] text-slate-500 font-mono">
            <span>Frame: {replayState.current_index} / {replayState.total_frames}</span>
            <span>{replayState.current_timestamp ? new Date(replayState.current_timestamp).toLocaleTimeString() : "--:--:--"}</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 transition-all duration-300"
              style={{
                width: `${Math.min(100, (replayState.current_index / Math.max(1, replayState.total_frames)) * 100)}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Generator Configuration Accordion/Controls */}
      <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex flex-col gap-2.5">
        <span className="text-[11px] font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5 text-indigo-500" />
          <span>Synthetic Trajectory Parameters</span>
        </span>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <label className="text-[10px] text-slate-400 block mb-0.5">Vehicles Count</label>
            <input
              type="number"
              min="2"
              max="50"
              value={numVehicles}
              onChange={(e) => setNumVehicles(e.target.value)}
              className="w-full px-2 py-1 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded text-slate-900 dark:text-white"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-0.5">Carpool Ratio</label>
            <select
              value={multiUserRatio}
              onChange={(e) => setMultiUserRatio(e.target.value)}
              className="w-full px-2 py-1 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded text-slate-900 dark:text-white"
            >
              <option value="0.2">20% Multi-User</option>
              <option value="0.5">50% Multi-User</option>
              <option value="0.8">80% Multi-User</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="w-full mt-1 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs rounded-lg transition shadow-xs flex items-center justify-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? "animate-spin" : ""}`} />
          <span>{isGenerating ? "Generating Trajectories..." : "Generate Road Trajectories"}</span>
        </button>
      </div>
    </div>
  );
};
