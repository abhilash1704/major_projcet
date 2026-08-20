import { useState } from "react";
import { useNavigationEngineContext } from "../../context/NavigationEngineContext";
import {
  Play,
  Pause,
  RotateCcw,
  Cpu,
  Car,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

/**
 * VehicleOverlay — Sprint 4.4
 *
 * Simulation control panel rendered as a floating overlay on the map.
 * Positioned bottom-right, above the existing map controls.
 *
 * Features:
 *   - Generate vehicles (configurable count, default 100)
 *   - Start / Pause / Resume / Reset simulation
 *   - Real-time stats: vehicle count, active, status, last update
 *   - Error state display
 *   - Collapsible to preserve map space
 */
export const VehicleOverlay = () => {
  const {
    vehicles,
    simulationStatus,
    simulationError,
    lastUpdateTime,
    handleGenerateVehicles,
    handleStartSimulation,
    handlePauseSimulation,
    handleResumeSimulation,
    handleResetSimulation,
    activeRoute,
  } = useNavigationEngineContext();

  const [generateCount, setGenerateCount] = useState(100);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const isRunning = simulationStatus === "running";
  const isPaused = simulationStatus === "paused";
  const isStarting = simulationStatus === "starting";
  const isError = simulationStatus === "error";
  const isIdle = simulationStatus === "idle";

  const activeVehicles = vehicles.filter((v) => v.status === "active").length;
  const totalVehicles = vehicles.length;

  const formatLastUpdate = () => {
    if (!lastUpdateTime) return "—";
    const diffMs = Date.now() - lastUpdateTime.getTime();
    const secs = Math.round(diffMs / 1000);
    if (secs < 5) return "just now";
    return `${secs}s ago`;
  };

  const statusColor = {
    idle: "text-slate-400",
    starting: "text-amber-400",
    running: "text-emerald-400",
    paused: "text-amber-300",
    error: "text-rose-400",
  }[simulationStatus] || "text-slate-400";

  const statusDot = {
    idle: "bg-slate-500",
    starting: "bg-amber-400 animate-pulse",
    running: "bg-emerald-400 animate-pulse",
    paused: "bg-amber-300",
    error: "bg-rose-500",
  }[simulationStatus] || "bg-slate-500";

  const statusLabel = {
    idle: "Idle",
    starting: "Starting…",
    running: "Running",
    paused: "Paused",
    error: "Error",
  }[simulationStatus] || "Idle";

  return (
    <div
      className="absolute bottom-6 right-4 z-[1000] pointer-events-auto"
      style={{ maxWidth: "220px" }}
    >
      <div className="bg-slate-900/95 backdrop-blur-sm border border-slate-700/80 rounded-2xl shadow-2xl text-xs font-sans overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-3 pt-2.5 pb-2 border-b border-slate-800">
          <div className="flex items-center gap-1.5 text-amber-400 font-semibold text-[11px]">
            <Car size={12} />
            Vehicle Simulation
          </div>
          <button
            onClick={() => setIsCollapsed((c) => !c)}
            className="text-slate-500 hover:text-slate-300 transition-colors"
            aria-label={isCollapsed ? "Expand" : "Collapse"}
          >
            {isCollapsed ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>

        {!isCollapsed && (
          <div className="px-3 py-2.5 space-y-3">
            {/* Stats Row */}
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px]">
              <div className="text-slate-500">Vehicles</div>
              <div className="text-slate-200 font-mono text-right">{totalVehicles}</div>
              <div className="text-slate-500">Active</div>
              <div className="text-slate-200 font-mono text-right">{activeVehicles}</div>
              <div className="text-slate-500">Status</div>
              <div className={`${statusColor} font-semibold text-right flex items-center justify-end gap-1`}>
                <span className={`w-1.5 h-1.5 rounded-full ${statusDot} inline-block`} />
                {statusLabel}
              </div>
              <div className="text-slate-500">Last Update</div>
              <div className="text-slate-300 font-mono text-right">{formatLastUpdate()}</div>
            </div>

            {/* Error Message */}
            {(simulationError || isError) && (
              <div className="flex items-start gap-1.5 text-[10px] text-rose-300 bg-rose-950/40 border border-rose-800/50 rounded-lg px-2 py-1.5">
                <AlertTriangle size={10} className="shrink-0 mt-0.5" />
                <span>{simulationError || "Simulation error. Check backend."}</span>
              </div>
            )}

            {/* Generate section */}
            <div className="space-y-1.5">
              <div className="text-[10px] text-slate-400 font-medium">Generate Vehicles</div>
              {activeRoute ? (
                <div className="text-[9px] text-emerald-400 flex items-center gap-1 mb-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"/>
                  Will place on active route
                </div>
              ) : (
                <div className="text-[9px] text-amber-400 flex items-center gap-1 mb-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block"/>
                  Calculate a route first
                </div>
              )}
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={generateCount}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    if (!isNaN(val) && val > 0 && val <= 500) setGenerateCount(val);
                  }}
                  className="w-16 bg-slate-800 border border-slate-600 text-slate-200 text-[11px] rounded-lg px-2 py-1 font-mono text-center focus:outline-none focus:border-amber-500"
                />
                <button
                  onClick={() => handleGenerateVehicles(generateCount)}
                  disabled={isStarting || isRunning || !activeRoute}
                  title={!activeRoute ? "Calculate a route first" : "Generate vehicles on route"}
                  className="flex-1 flex items-center justify-center gap-1 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-[11px] font-semibold rounded-lg px-2 py-1.5 transition-colors"
                >
                  {isStarting ? (
                    <Loader2 size={10} className="animate-spin" />
                  ) : (
                    <Cpu size={10} />
                  )}
                  Generate
                </button>
              </div>
            </div>

            {/* Simulation Controls */}
            <div className="space-y-1.5">
              <div className="text-[10px] text-slate-400 font-medium">Controls</div>
              <div className="grid grid-cols-2 gap-1.5">
                {/* Start or Pause/Resume */}
                {isIdle && (
                  <button
                    onClick={handleStartSimulation}
                    disabled={totalVehicles === 0}
                    className="col-span-2 flex items-center justify-center gap-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:bg-slate-700 disabled:text-slate-500 text-white text-[11px] font-semibold rounded-lg px-2 py-1.5 transition-colors"
                  >
                    <Play size={10} />
                    Start Simulation
                  </button>
                )}

                {isRunning && (
                  <button
                    onClick={handlePauseSimulation}
                    className="col-span-2 flex items-center justify-center gap-1.5 bg-amber-700 hover:bg-amber-600 text-white text-[11px] font-semibold rounded-lg px-2 py-1.5 transition-colors"
                  >
                    <Pause size={10} />
                    Pause
                  </button>
                )}

                {isPaused && (
                  <button
                    onClick={handleResumeSimulation}
                    className="col-span-2 flex items-center justify-center gap-1.5 bg-emerald-700 hover:bg-emerald-600 text-white text-[11px] font-semibold rounded-lg px-2 py-1.5 transition-colors"
                  >
                    <Play size={10} />
                    Resume
                  </button>
                )}

                {isError && (
                  <button
                    onClick={handleStartSimulation}
                    disabled={totalVehicles === 0}
                    className="col-span-2 flex items-center justify-center gap-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:bg-slate-700 disabled:text-slate-500 text-white text-[11px] font-semibold rounded-lg px-2 py-1.5 transition-colors"
                  >
                    <Play size={10} />
                    Retry
                  </button>
                )}

                {/* Reset always available */}
                <button
                  onClick={handleResetSimulation}
                  className="col-span-2 flex items-center justify-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 text-[11px] font-semibold rounded-lg px-2 py-1.5 transition-colors"
                >
                  <RotateCcw size={10} />
                  Reset
                </button>
              </div>
            </div>

            {/* Ready status hint */}
            {isIdle && totalVehicles > 0 && !simulationError && (
              <div className="flex items-center gap-1 text-[10px] text-emerald-400">
                <CheckCircle2 size={10} />
                {totalVehicles} vehicles ready
              </div>
            )}
          </div>
        )}

        {/* Collapsed mini-status */}
        {isCollapsed && (
          <div className="px-3 py-1.5 flex items-center gap-2 text-[10px]">
            <span className={`w-1.5 h-1.5 rounded-full ${statusDot} inline-block`} />
            <span className={statusColor}>{statusLabel}</span>
            {totalVehicles > 0 && (
              <span className="text-slate-500 ml-auto">{totalVehicles} veh</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
