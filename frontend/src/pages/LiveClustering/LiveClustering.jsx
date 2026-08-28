/**
 * LiveClustering.jsx — LIVE VEHICLE CLUSTERING Dashboard Page
 *
 * Restructured hierarchy for 5-10s visual understanding:
 * 1. Top Header, Control Bar & Live Status Strip
 * 2. Primary Map view (~70% desktop width) with clean markers & cluster count badges
 * 3. Right Analysis Flow Panel (~30% desktop width) presenting the 5-step visual story
 * 4. Low-prominence bottom system status bar
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
      {/* ── 1. Top Analysis Header, Controls & Live Status Strip ────────── */}
      <TopAnalysisBar />

      {/* ── 2. Main Content Split: Left Map Column | Right Analysis Sidebar */}
      <div className="flex-1 w-full flex flex-col lg:flex-row overflow-hidden relative">
        
        {/* Left Primary Map Container (~70% width on Desktop) */}
        <div className="flex-1 lg:w-[65%] xl:w-[70%] h-full relative flex flex-col border-r border-slate-200 dark:border-slate-800 overflow-hidden">
          <LiveClusteringMap />
          <ClusterDetailsPanel />
          {/* Low prominence health status bar */}
          <BottomMetricsBar />
        </div>

        {/* Right Analysis Flow Sidebar (~30% width on Desktop) */}
        <aside className="w-full lg:w-[380px] xl:w-[420px] h-full overflow-y-auto p-4 bg-slate-100/60 dark:bg-surface-dark/40 shrink-0 z-20">
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
