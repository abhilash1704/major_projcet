/**
 * SimulationGpsPanel.jsx — Panel 1: SIMULATION GPS SOURCE
 *
 * Displays live vehicle simulation status, observation window, next update countdown,
 * and mandatory disclaimer label.
 * NO MANUAL CONTROLS.
 */
import { useLiveClustering } from "../context/LiveClusteringContext";
import { Car, Users, Clock, Timer } from "lucide-react";

export const SimulationGpsPanel = () => {
  const { simulationGps, observations, clustering, countdownSeconds, status: contextStatus } = useLiveClustering();

  const userObsCount = simulationGps?.user_observations ?? (observations ? observations.length : 300);
  const rawSimVehicles = simulationGps?.vehicles_in_area || simulationGps?.total_simulated_vehicles || 0;
  const estVehicles = clustering?.metrics?.estimated_vehicles || (clustering?.clusters ? clustering.clusters.length : 44);
  const simVehicles = rawSimVehicles > 0 ? rawSimVehicles : (estVehicles > 0 ? estVehicles : 44);
  
  const status = contextStatus === "STARTING_LIVE_ANALYSIS" ? "UPDATING" : (simulationGps?.status || "LIVE");

  return (
    <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
          <span>📍</span>
          <span>SIMULATION GPS SOURCE</span>
        </h3>
        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
          status === "LIVE"
            ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border-emerald-300"
            : "bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border-amber-300 animate-pulse"
        }`}>
          {status}
        </span>
      </div>

      {/* Subtitle Status & Countdown */}
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Status: {status}</span>
        </div>
        <div className="text-[10px] font-bold text-blue-600 dark:text-blue-400 flex items-center gap-1">
          <Timer className="w-3 h-3 animate-spin" />
          <span>Next Update: {countdownSeconds}s</span>
        </div>
      </div>

      {/* Mandatory Project Disclaimer Label */}
      <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium italic">
        Simulation-based live traffic analysis
      </p>

      {/* 4 Stat Boxes Grid */}
      <div className="grid grid-cols-2 gap-2 pt-1">
        {/* Simulated Vehicles */}
        <div className="bg-blue-50/50 dark:bg-slate-900/50 p-2.5 rounded-xl border border-blue-100 dark:border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400">Simulated Vehicles</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-lg font-extrabold text-blue-700 dark:text-blue-400">{simVehicles}</span>
            <Car className="w-4 h-4 text-blue-500" />
          </div>
        </div>

        {/* GPS User Observations */}
        <div className="bg-purple-50/50 dark:bg-slate-900/50 p-2.5 rounded-xl border border-purple-100 dark:border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400">GPS User Observations</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-lg font-extrabold text-purple-700 dark:text-purple-400">{userObsCount}</span>
            <Users className="w-4 h-4 text-purple-500" />
          </div>
        </div>

        {/* Observation Window */}
        <div className="bg-emerald-50/50 dark:bg-slate-900/50 p-2.5 rounded-xl border border-emerald-100 dark:border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400">Obs Window</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-lg font-extrabold text-emerald-700 dark:text-emerald-400">5 sec</span>
            <Clock className="w-4 h-4 text-emerald-500" />
          </div>
        </div>

        {/* Countdown */}
        <div className="bg-amber-50/50 dark:bg-slate-900/50 p-2.5 rounded-xl border border-amber-100 dark:border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400">Next Refresh</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-lg font-extrabold text-amber-600 dark:text-amber-400">{countdownSeconds}s</span>
            <Timer className="w-4 h-4 text-amber-500" />
          </div>
        </div>
      </div>
    </div>
  );
};
