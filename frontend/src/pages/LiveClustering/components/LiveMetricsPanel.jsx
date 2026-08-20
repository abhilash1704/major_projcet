/**
 * LiveMetricsPanel.jsx — Sidebar Container for 5 Real-Time Analytics Panels
 */
import { SimulationGpsPanel } from "./SimulationGpsPanel";
import { VehicleClusteringPanel } from "./VehicleClusteringPanel";
import { RoadDensityPanel } from "./RoadDensityPanel";
import { EvaluationPanel } from "./EvaluationPanel";
import { TrafficPanel } from "./TrafficPanel";
import { useLiveClustering } from "../context/LiveClusteringContext";

export const LiveMetricsPanel = () => {
  const { error } = useLiveClustering();

  return (
    <div className="flex flex-col gap-3.5 pb-4">
      {/* Error Alert if any */}
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 rounded-xl text-xs text-red-700 dark:text-red-300">
          <span className="font-semibold block mb-0.5">Analysis Alert</span>
          <span>{error}</span>
        </div>
      )}

      {/* Panel 1: SIMULATION GPS SOURCE */}
      <SimulationGpsPanel />

      {/* Panel 2: DBSCAN CLUSTERING */}
      <VehicleClusteringPanel />

      {/* Panel 3: ROAD VEHICLE DENSITY */}
      <RoadDensityPanel />

      {/* Panel 4: CLUSTERING EVALUATION */}
      <EvaluationPanel />

      {/* Panel 5: REAL TRAFFIC (EXTERNAL PROVIDER) */}
      <TrafficPanel />
    </div>
  );
};
