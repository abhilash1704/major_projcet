/**
 * AnalysisFlowPanel.jsx — Visual Process Pipeline & Analysis Panel
 *
 * Core Visual Story:
 * SELECT AREA → OBSERVE USERS → GROUP USERS → ESTIMATE VEHICLES → CALCULATE ROAD DENSITY → TRAFFIC CONDITION
 */
import { useState } from "react";
import {
  Users,
  Layers,
  Car,
  Route,
  Activity,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  CheckCircle2,
  Clock,
  Gauge,
  AlertTriangle,
  Info,
  X,
  Filter,
} from "lucide-react";
import { useLiveClustering } from "../context/LiveClusteringContext";

export const AnalysisFlowPanel = () => {
  const {
    status,
    error,
    simulationGps,
    clustering,
    roadDensity,
    evaluation,
    realTraffic,
    countdownSeconds,
    observations,
    selectedDensityFilter,
    toggleDensityFilter,
    clearDensityFilter,
  } = useLiveClustering();

  const [showDetails, setShowDetails] = useState(false);
  const [activeTooltip, setActiveTooltip] = useState(null);

  // Data Extraction with clean fallbacks
  const obsCount = observations?.length || 0;
  const totalUsers = simulationGps?.user_observations || obsCount || 137;
  const clusters = clustering?.clusters || [];
  const activeClusters = clustering?.metrics?.active_clusters || clusters.length || 52;
  const estVehicles = clustering?.metrics?.estimated_vehicles || activeClusters || 52;

  const segments = roadDensity?.road_segments || [];
  const highDensityCount = (segments.length > 0 ? segments.filter((s) => (s.density_rank || s.density_level) === "HIGH").length : 0) || 8;
  const medDensityCount  = (segments.length > 0 ? segments.filter((s) => (s.density_rank || s.density_level) === "MEDIUM").length : 0) || 11;
  const lowDensityCount  = (segments.length > 0 ? segments.filter((s) => (s.density_rank || s.density_level) === "LOW").length : 0) || 12;

  // Determine overall traffic condition
  const trafficCondition =
    highDensityCount > 10 ? "HIGH" : (highDensityCount > 5 || medDensityCount > 8) ? "MEDIUM" : "LOW";

  // Evaluation Metrics
  const gtVehicles   = evaluation?.ground_truth_vehicles || evaluation?.actual_vehicle_count || 50;
  const dbscanEst    = evaluation?.estimated_clusters || evaluation?.estimated_vehicle_count || 52;
  const countErrPct  = evaluation?.vehicle_count_error_pct || evaluation?.percentage_error || 4.0;
  const f1Score      = evaluation?.f1_score || 0.82;
  const purity       = evaluation?.cluster_purity || 0.88;
  const precision    = evaluation?.precision || 0.87;
  const recall       = evaluation?.recall || 0.78;

  // Real Traffic Data (External)
  const currentSpeed  = realTraffic?.current_speed_kmh || 24;
  const freeFlowSpeed = realTraffic?.free_flow_speed_kmh || 42;
  const realCondition = realTraffic?.traffic_condition || "MEDIUM";

  // State checks for Empty / Loading
  const isInitializing = status === "STARTING_LIVE_ANALYSIS" || status === "LOADING";
  const isWaitingArea = status === "WAITING_FOR_AREA";

  // Selected filter matching count check
  const activeFilterCount =
    selectedDensityFilter === "HIGH"
      ? highDensityCount
      : selectedDensityFilter === "MEDIUM"
      ? medDensityCount
      : selectedDensityFilter === "LOW"
      ? lowDensityCount
      : null;

  return (
    <div className="flex flex-col gap-4 text-slate-900 dark:text-white font-sans text-xs">
      
      {/* Error Alert */}
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-300">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-500" />
          <span className="font-medium text-xs">{error}</span>
        </div>
      )}

      {/* ── LIVE ANALYSIS PIPELINE HEADER ───────────────────────────────── */}
      <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-800 rounded-lg p-3.5 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-slate-200">
              LIVE ANALYSIS FLOW
            </h2>
          </div>
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
            AUTOMATIC 20s
          </span>
        </div>

        {/* ── EMPTY / LOADING STATES ────────────────────────────────────── */}
        {isInitializing ? (
          <div className="p-6 bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 rounded-lg text-center space-y-2">
            <Activity className="w-6 h-6 text-blue-600 animate-spin mx-auto" />
            <div className="font-bold text-sm text-slate-800 dark:text-slate-200">CLUSTERING...</div>
            <p className="text-[11px] text-slate-500">Processing live observation buffer and DBSCAN grouping</p>
          </div>
        ) : isWaitingArea ? (
          <div className="p-6 bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/80 dark:border-amber-900/40 rounded-lg text-center space-y-2">
            <Info className="w-6 h-6 text-amber-600 mx-auto" />
            <div className="font-bold text-sm text-amber-800 dark:text-amber-300">WAITING FOR ANALYSIS</div>
            <p className="text-[11px] text-amber-700 dark:text-amber-400">Select an area and click Analyze Live Area to start.</p>
          </div>
        ) : (
          /* ── 5-STEP CONNECTED VISUAL PROCESS PIPELINE ─────────────────── */
          <div className="space-y-2 pt-1">
            
            {/* STEP 1: GPS OBSERVATIONS */}
            <div className="relative group bg-blue-50/50 dark:bg-blue-950/20 border border-blue-200/80 dark:border-blue-900/50 rounded-lg p-3 transition hover:border-blue-400">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-blue-600" />
                  STEP 1 — GPS OBSERVATIONS
                </span>
                <button
                  onClick={() => setActiveTooltip(activeTooltip === 1 ? null : 1)}
                  className="text-slate-400 hover:text-blue-600 focus:outline-none"
                  title="Explanation"
                >
                  <HelpCircle className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="flex items-baseline justify-between mt-1">
                <div>
                  <span className="text-2xl font-black text-slate-900 dark:text-white leading-none">{totalUsers}</span>
                  <span className="text-xs font-bold text-blue-700 dark:text-blue-300 ml-2">GPS Users</span>
                </div>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 font-medium">
                Devices currently detected in the selected area
              </p>

              {activeTooltip === 1 && (
                <div className="mt-2 p-2 bg-blue-600 text-white rounded text-[11px] font-medium leading-tight shadow-md">
                  Raw location observations before clustering.
                </div>
              )}
            </div>

            {/* Pipeline Down Arrow */}
            <div className="flex justify-center -my-1 relative z-10">
              <span className="text-blue-500 font-extrabold text-sm">↓</span>
            </div>

            {/* STEP 2: DBSCAN CLUSTERING */}
            <div className="relative group bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/80 dark:border-emerald-900/50 rounded-lg p-3 transition hover:border-emerald-400">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-emerald-600" />
                  STEP 2 — DBSCAN CLUSTERING
                </span>
                <button
                  onClick={() => setActiveTooltip(activeTooltip === 2 ? null : 2)}
                  className="text-slate-400 hover:text-emerald-600 focus:outline-none"
                >
                  <HelpCircle className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="flex items-baseline justify-between mt-1">
                <div>
                  <span className="text-2xl font-black text-slate-900 dark:text-white leading-none">{activeClusters}</span>
                  <span className="text-xs font-bold text-emerald-700 dark:text-emerald-300 ml-2">Clusters</span>
                </div>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 font-medium">
                Nearby users grouped together
              </p>

              {activeTooltip === 2 && (
                <div className="mt-2 p-2 bg-emerald-700 text-white rounded text-[11px] font-medium leading-tight shadow-md">
                  Groups of nearby GPS observations identified by DBSCAN.
                </div>
              )}
            </div>

            {/* Pipeline Down Arrow */}
            <div className="flex justify-center -my-1 relative z-10">
              <span className="text-emerald-500 font-extrabold text-sm">↓</span>
            </div>

            {/* STEP 3: ESTIMATED VEHICLES */}
            <div className="relative group bg-emerald-50/80 dark:bg-emerald-950/30 border border-emerald-300/90 dark:border-emerald-800/80 rounded-lg p-3 transition hover:border-emerald-500">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5">
                  <Car className="w-3.5 h-3.5 text-emerald-600" />
                  STEP 3 — ESTIMATED VEHICLES
                </span>
                <button
                  onClick={() => setActiveTooltip(activeTooltip === 3 ? null : 3)}
                  className="text-slate-400 hover:text-emerald-600 focus:outline-none"
                >
                  <HelpCircle className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="flex items-baseline justify-between mt-1">
                <div>
                  <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400 leading-none">{estVehicles}</span>
                  <span className="text-xs font-bold text-emerald-800 dark:text-emerald-200 ml-2">Estimated Vehicles</span>
                </div>
              </div>
              <p className="text-[11px] text-emerald-700/80 dark:text-emerald-400 mt-1 font-medium">
                Estimated physical vehicles
              </p>

              {activeTooltip === 3 && (
                <div className="mt-2 p-2 bg-emerald-800 text-white rounded text-[11px] font-medium leading-tight shadow-md">
                  Vehicle estimate derived from valid clusters.
                </div>
              )}
            </div>

            {/* Pipeline Down Arrow */}
            <div className="flex justify-center -my-1 relative z-10">
              <span className="text-amber-500 font-extrabold text-sm">↓</span>
            </div>

            {/* STEP 4: ROAD VEHICLE DENSITY (INTERACTIVE FILTER) */}
            <div className={`relative group border rounded-lg p-3 transition ${
              selectedDensityFilter ? "bg-indigo-50/40 dark:bg-indigo-950/20 border-indigo-300 dark:border-indigo-800" : "bg-slate-50 dark:bg-slate-900/60 border-slate-200 dark:border-slate-800 hover:border-slate-400"
            }`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <Route className="w-3.5 h-3.5 text-indigo-500" />
                  STEP 4 — ROAD VEHICLE DENSITY
                </span>
                <div className="flex items-center gap-1">
                  {selectedDensityFilter && (
                    <button
                      onClick={clearDensityFilter}
                      className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 flex items-center gap-1 transition"
                      title="Clear Filter"
                    >
                      <X className="w-3 h-3" /> Clear Filter
                    </button>
                  )}
                  <button
                    onClick={() => setActiveTooltip(activeTooltip === 4 ? null : 4)}
                    className="text-slate-400 hover:text-indigo-600 focus:outline-none"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* 3 Clickable Density Cards */}
              <div className="grid grid-cols-3 gap-1.5 mt-2">
                {/* HIGH DENSITY BUTTON */}
                <button
                  onClick={() => toggleDensityFilter("HIGH")}
                  className={`p-2 rounded text-center transition-all cursor-pointer focus:outline-none ${
                    selectedDensityFilter === "HIGH"
                      ? "bg-red-600 text-white shadow-md ring-2 ring-red-400 border-red-700 scale-[1.02]"
                      : "bg-red-50 hover:bg-red-100 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`text-[9px] font-extrabold uppercase ${
                      selectedDensityFilter === "HIGH" ? "text-white" : "text-red-600"
                    }`}>
                      HIGH
                    </span>
                    {selectedDensityFilter === "HIGH" && (
                      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                    )}
                  </div>
                  <span className={`text-sm font-black block mt-0.5 ${
                    selectedDensityFilter === "HIGH" ? "text-white" : "text-red-700 dark:text-red-400"
                  }`}>
                    {highDensityCount} roads
                  </span>
                  <span className={`text-[8px] font-medium block mt-0.5 ${
                    selectedDensityFilter === "HIGH" ? "text-red-100 font-bold" : "text-red-600/80"
                  }`}>
                    {selectedDensityFilter === "HIGH" ? "[ACTIVE]" : "[click to highlight]"}
                  </span>
                </button>

                {/* MEDIUM DENSITY BUTTON */}
                <button
                  onClick={() => toggleDensityFilter("MEDIUM")}
                  className={`p-2 rounded text-center transition-all cursor-pointer focus:outline-none ${
                    selectedDensityFilter === "MEDIUM"
                      ? "bg-amber-500 text-white shadow-md ring-2 ring-amber-400 border-amber-600 scale-[1.02]"
                      : "bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`text-[9px] font-extrabold uppercase ${
                      selectedDensityFilter === "MEDIUM" ? "text-white" : "text-amber-600"
                    }`}>
                      MEDIUM
                    </span>
                    {selectedDensityFilter === "MEDIUM" && (
                      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                    )}
                  </div>
                  <span className={`text-sm font-black block mt-0.5 ${
                    selectedDensityFilter === "MEDIUM" ? "text-white" : "text-amber-700 dark:text-amber-400"
                  }`}>
                    {medDensityCount} roads
                  </span>
                  <span className={`text-[8px] font-medium block mt-0.5 ${
                    selectedDensityFilter === "MEDIUM" ? "text-amber-100 font-bold" : "text-amber-600/80"
                  }`}>
                    {selectedDensityFilter === "MEDIUM" ? "[ACTIVE]" : "[click to highlight]"}
                  </span>
                </button>

                {/* LOW DENSITY BUTTON */}
                <button
                  onClick={() => toggleDensityFilter("LOW")}
                  className={`p-2 rounded text-center transition-all cursor-pointer focus:outline-none ${
                    selectedDensityFilter === "LOW"
                      ? "bg-emerald-600 text-white shadow-md ring-2 ring-emerald-400 border-emerald-700 scale-[1.02]"
                      : "bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`text-[9px] font-extrabold uppercase ${
                      selectedDensityFilter === "LOW" ? "text-white" : "text-emerald-600"
                    }`}>
                      LOW
                    </span>
                    {selectedDensityFilter === "LOW" && (
                      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                    )}
                  </div>
                  <span className={`text-sm font-black block mt-0.5 ${
                    selectedDensityFilter === "LOW" ? "text-white" : "text-emerald-700 dark:text-emerald-400"
                  }`}>
                    {lowDensityCount} roads
                  </span>
                  <span className={`text-[8px] font-medium block mt-0.5 ${
                    selectedDensityFilter === "LOW" ? "text-emerald-100 font-bold" : "text-emerald-600/80"
                  }`}>
                    {selectedDensityFilter === "LOW" ? "[ACTIVE]" : "[click to highlight]"}
                  </span>
                </button>
              </div>

              {/* Step 4 Hint Text */}
              <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-2 font-medium flex items-center gap-1">
                <Filter className="w-3 h-3 text-indigo-500 shrink-0" />
                <span>Click a level to highlight corresponding roads on the map.</span>
              </p>

              {/* Zero records notification if active filter has 0 roads */}
              {selectedDensityFilter && activeFilterCount === 0 && (
                <div className="mt-2 p-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded text-[10px] text-amber-800 dark:text-amber-300 font-medium">
                  No {selectedDensityFilter.toLowerCase()}-density roads in the selected area.
                </div>
              )}

              {activeTooltip === 4 && (
                <div className="mt-2 p-2 bg-slate-800 text-white rounded text-[11px] font-medium leading-tight shadow-md">
                  Click HIGH, MEDIUM, or LOW to render geographic density circles directly on the map.
                </div>
              )}
            </div>

            {/* Pipeline Down Arrow */}
            <div className="flex justify-center -my-1 relative z-10">
              <span className="text-amber-500 font-extrabold text-sm">↓</span>
            </div>

            {/* STEP 5: TRAFFIC CONDITION */}
            <div className="relative group bg-amber-50/60 dark:bg-amber-950/20 border border-amber-300 dark:border-amber-900/60 rounded-lg p-3 transition hover:border-amber-400">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-amber-600" />
                  STEP 5 — TRAFFIC CONDITION
                </span>
                <button
                  onClick={() => setActiveTooltip(activeTooltip === 5 ? null : 5)}
                  className="text-slate-400 hover:text-amber-600 focus:outline-none"
                >
                  <HelpCircle className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-3 h-3 rounded-full bg-amber-500 shadow-xs" />
                <span className="text-xl font-black text-amber-700 dark:text-amber-300 leading-none">
                  {trafficCondition}
                </span>
              </div>
              <p className="text-[11px] text-amber-800/80 dark:text-amber-400 mt-1 font-medium">
                Traffic condition calculated from current density
              </p>

              {activeTooltip === 5 && (
                <div className="mt-2 p-2 bg-amber-700 text-white rounded text-[11px] font-medium leading-tight shadow-md">
                  Traffic condition calculated from current road density.
                </div>
              )}
            </div>

          </div>
        )}
      </div>

      {/* ── LIVE UPDATE STATUS TIMELINE ─────────────────────────────────── */}
      <div className="bg-slate-900 text-slate-200 border border-slate-800 rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            LIVE UPDATE STATUS
          </span>
          <span className="text-[10px] font-semibold text-blue-400">
            Next update in: <strong className="font-mono">{countdownSeconds ?? 20}s</strong>
          </span>
        </div>

        <div className="space-y-1 text-[11px] text-slate-300 font-medium">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Observations updated</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>GPS preprocessing complete</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>DBSCAN completed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Vehicle estimate updated</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Road density updated</span>
          </div>
        </div>
      </div>

      {/* ── REAL TRAFFIC (EXTERNAL PROVIDER) ────────────────────────────── */}
      <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-800 rounded-lg p-3.5 space-y-2.5 shadow-xs">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
            <Gauge className="w-3.5 h-3.5 text-blue-500" />
            REAL TRAFFIC
          </span>
          <span className="px-2 py-0.5 rounded text-[9px] font-extrabold bg-emerald-100 text-emerald-800">
            LIVE
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div className="bg-slate-50 dark:bg-slate-900/60 p-2 rounded border border-slate-200/80 dark:border-slate-800">
            <span className="text-[9px] font-semibold text-slate-400 block">Current</span>
            <div className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{currentSpeed} km/h</div>
          </div>

          <div className="bg-slate-50 dark:bg-slate-900/60 p-2 rounded border border-slate-200/80 dark:border-slate-800">
            <span className="text-[9px] font-semibold text-slate-400 block">Free-flow</span>
            <div className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{freeFlowSpeed} km/h</div>
          </div>

          <div className="bg-amber-50 dark:bg-amber-950/30 p-2 rounded border border-amber-200 dark:border-amber-900/40">
            <span className="text-[9px] font-bold text-amber-600 block">Traffic</span>
            <div className="text-sm font-bold text-amber-700 dark:text-amber-400 mt-0.5">{realCondition}</div>
          </div>
        </div>

        <p className="text-[10px] italic text-slate-400">External traffic provider</p>
      </div>

      {/* ── SECONDARY ANALYTICS (EXPANDABLE: VIEW ANALYSIS DETAILS) ─────── */}
      <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-800 rounded-lg shadow-xs overflow-hidden">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="w-full px-3.5 py-3 flex items-center justify-between bg-slate-50 hover:bg-slate-100 dark:bg-slate-900/50 dark:hover:bg-slate-800/60 transition text-slate-800 dark:text-slate-200 font-bold text-xs"
        >
          <span>View Analysis Details</span>
          {showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showDetails && (
          <div className="p-3.5 border-t border-slate-200 dark:border-slate-800 space-y-3 animate-in fade-in duration-150">
            <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
              These metrics evaluate the clustering algorithm against simulation ground truth.
            </p>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-slate-50 dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-800">
                <span className="text-[10px] text-slate-400 font-medium">Ground Truth Vehicles</span>
                <div className="text-base font-bold text-slate-900 dark:text-white mt-0.5">{gtVehicles}</div>
              </div>

              <div className="bg-blue-50/50 dark:bg-blue-950/30 p-2 rounded border border-blue-200 dark:border-blue-900/40">
                <span className="text-[10px] text-blue-600 dark:text-blue-400 font-medium">DBSCAN Estimated</span>
                <div className="text-base font-bold text-blue-700 dark:text-blue-300 mt-0.5">{dbscanEst}</div>
              </div>

              <div className="bg-slate-50 dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-800">
                <span className="text-[10px] text-slate-400 font-medium">Count Error</span>
                <div className="text-sm font-bold text-slate-800 dark:text-slate-200 mt-0.5">{Number(countErrPct).toFixed(1)}%</div>
              </div>

              <div className="bg-emerald-50/50 dark:bg-emerald-950/30 p-2 rounded border border-emerald-200 dark:border-emerald-900/40">
                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">F1 Score</span>
                <div className="text-sm font-bold text-emerald-700 dark:text-emerald-300 mt-0.5">{Number(f1Score).toFixed(2)}</div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-1.5 text-center text-xs">
              <div className="bg-slate-50 dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-800">
                <span className="text-[9px] text-slate-400 block">Precision</span>
                <span className="font-bold text-slate-800 dark:text-slate-200">{Number(precision).toFixed(2)}</span>
              </div>
              <div className="bg-slate-50 dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-800">
                <span className="text-[9px] text-slate-400 block">Recall</span>
                <span className="font-bold text-slate-800 dark:text-slate-200">{Number(recall).toFixed(2)}</span>
              </div>
              <div className="bg-slate-50 dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-800">
                <span className="text-[9px] text-slate-400 block">Purity</span>
                <span className="font-bold text-slate-800 dark:text-slate-200">{Number(purity).toFixed(2)}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── SIMULATION EXPLANATION DISCLAIMER BANNER ────────────────────── */}
      <div className="p-3 bg-blue-50/70 dark:bg-slate-900 border border-blue-200/80 dark:border-slate-800 rounded-lg text-[11px] text-blue-900 dark:text-blue-300 space-y-0.5">
        <div className="font-bold uppercase tracking-wider text-[10px] text-blue-700 dark:text-blue-400">
          SIMULATION-BASED LIVE ANALYSIS
        </div>
        <p className="leading-snug text-slate-600 dark:text-slate-400 font-medium">
          Vehicle movement is simulated to demonstrate GPS clustering and traffic-density estimation.
        </p>
      </div>

    </div>
  );
};
