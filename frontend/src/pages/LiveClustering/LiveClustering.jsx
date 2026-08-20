/**
 * LiveClustering.jsx — LIVE VEHICLE CLUSTERING Dashboard Page
 */
import { AppLayout } from "../../modules/layout/components/AppLayout";
import { LiveClusteringProvider } from "./context/LiveClusteringContext";
import { TopAnalysisBar } from "./components/TopAnalysisBar";
import { LiveClusteringMap } from "./components/LiveClusteringMap";
import { BottomMetricsBar } from "./components/BottomMetricsBar";
import { LiveMetricsPanel } from "./components/LiveMetricsPanel";
import { ClusterDetailsPanel } from "./components/ClusterDetailsPanel";

const LiveClusteringInner = () => {
  return (
    <div className="flex-1 h-full w-full flex flex-col overflow-hidden relative bg-slate-50 dark:bg-background-dark">
      {/* Top Analysis & Area Selection Bar */}
      <TopAnalysisBar />

      {/* Main Content Split: Left Map & Bottom Bar | Right Analytics Sidebar */}
      <div className="flex-1 w-full flex flex-col lg:flex-row overflow-hidden relative">
        {/* Left Column: Interactive Leaflet Map + Bottom Metrics Summary Bar */}
        <div className="flex-1 lg:w-[65%] xl:w-[70%] h-full relative flex flex-col border-r border-slate-200 dark:border-slate-800 overflow-hidden">
          <LiveClusteringMap />
          <ClusterDetailsPanel />
          <BottomMetricsBar />
        </div>

        {/* Right Column: 5 Real-Time Analytics Panels */}
        <aside className="w-full lg:w-[380px] xl:w-[420px] h-full overflow-y-auto p-4 bg-slate-100/60 dark:bg-surface-dark/40 flex flex-col gap-4 shrink-0 z-20">
          <LiveMetricsPanel />
        </aside>
      </div>
    </div>
  );
};

export const LiveClustering = () => (
  <AppLayout>
    <LiveClusteringProvider>
      <LiveClusteringInner />
    </LiveClusteringProvider>
  </AppLayout>
);
