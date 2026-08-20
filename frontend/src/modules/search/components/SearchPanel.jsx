import { useState } from "react";
import { SearchInput } from "./SearchInput";
import { SwapButton } from "./SwapButton";
import { ClearButton } from "./ClearButton";
import { CurrentLocationButton } from "./CurrentLocationButton";
import { SearchButton } from "./SearchButton";
import { RoadNodeDiagnostic } from "./RoadNodeDiagnostic";
import { useSearchPanel } from "../hooks/useSearchPanel";
import { useLocationSearch } from "../hooks/useLocationSearch";
import { useNavigationEngineContext } from "../../navigation-engine/context/NavigationEngineContext";
import {
  Navigation,
  ChevronUp,
  ChevronDown,
  AlertCircle,
  Info,
  MapPin,
  Loader2,
  CheckCircle2,
} from "lucide-react";

/**
 * SearchPanel — Sprint 5.4
 *
 * Floating search UI connected to real Nominatim geocoding and Road Network Engine.
 * Shows subtle road-node resolution status badges for source & destination.
 */
export const SearchPanel = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // ── Context state for road nodes & algorithm ──────────────────────────────
  const {
    sourceRoadNode,
    destinationRoadNode,
    sourceNodeLoading,
    destinationNodeLoading,
    sourceNodeError,
    destinationNodeError,
    selectedAlgorithm,
    setSelectedAlgorithm,
    selectedRoutingMode,
    setSelectedRoutingMode,
  } = useNavigationEngineContext();

  // ── Panel-level state (text, locations, swap, clear, geo) ─────────────
  const {
    sourceText,
    destinationText,
    isSearching,
    searchError,
    searchInfo,
    geoLoading,
    handleSourceChange,
    handleDestinationChange,
    handleSwap,
    handleClear,
    handleUseCurrentLocation,
    handleSearchRoute,
    setSourceResolved,
    setDestinationResolved,
  } = useSearchPanel();

  // ── Independent Nominatim search state per field ───────────────────────
  const sourceSearch = useLocationSearch();
  const destSearch = useLocationSearch();

  // ── Result selection handlers ──────────────────────────────────────────
  const handleSelectSource = (result) => {
    handleSourceChange(result.displayName);
    setSourceResolved({
      placeId: result.placeId,
      displayName: result.displayName,
      latitude: result.latitude,
      longitude: result.longitude,
    });
    sourceSearch.clearResults();
  };

  const handleSelectDest = (result) => {
    handleDestinationChange(result.displayName);
    setDestinationResolved({
      placeId: result.placeId,
      displayName: result.displayName,
      latitude: result.latitude,
      longitude: result.longitude,
    });
    destSearch.clearResults();
  };

  // ── Text change handlers — also trigger Nominatim search ───────────────
  const handleSourceTextChange = (text) => {
    handleSourceChange(text);
    sourceSearch.search(text);
  };

  const handleDestTextChange = (text) => {
    handleDestinationChange(text);
    destSearch.search(text);
  };

  // ── Clear — also clear both search results ─────────────────────────────
  const handleClearAll = () => {
    handleClear();
    sourceSearch.clearResults();
    destSearch.clearResults();
  };

  return (
    <div className="w-full max-w-[340px] sm:max-w-[400px] bg-white/95 dark:bg-surface-dark/95 backdrop-blur-md rounded-2xl border border-slate-200/80 dark:border-slate-700/60 shadow-2xl transition-all duration-200 pointer-events-auto overflow-visible">

      {/* ── Header ── */}
      <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-slate-100 dark:border-slate-800/80 rounded-t-2xl">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10 text-primary dark:bg-primary/20">
            <Navigation size={15} />
          </div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight">
            Plan Route
          </h3>
        </div>

        <button
          onClick={() => setIsCollapsed((v) => !v)}
          aria-label={isCollapsed ? "Expand search panel" : "Collapse search panel"}
          className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          {isCollapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
        </button>
      </div>

      {/* ── Body ── */}
      {!isCollapsed && (
        <div className="px-4 pb-4 pt-3 space-y-3">

          {/* Inputs + Swap */}
          <div className="flex items-start gap-2">
            <div className="flex-1 flex flex-col gap-2.5">

              {/* Source input */}
              <div>
                <SearchInput
                  placeholder="Search starting location..."
                  value={sourceText}
                  onChange={handleSourceTextChange}
                  onClear={() => {
                    handleSourceChange("");
                    sourceSearch.clearResults();
                  }}
                  onSelectResult={handleSelectSource}
                  onSelectCurrentLocation={handleUseCurrentLocation}
                  icon={geoLoading ? Loader2 : Navigation}
                  iconColor={geoLoading ? "text-slate-400 animate-spin" : "text-primary"}
                  results={sourceSearch.results}
                  loading={sourceSearch.loading}
                  searchError={sourceSearch.error}
                  aria-label="Starting location"
                />

                {/* Subtle Source Road Node status */}
                {sourceNodeLoading && (
                  <div className="mt-1 flex items-center gap-1.5 text-[11px] text-amber-600 dark:text-amber-400 font-medium px-1">
                    <Loader2 size={11} className="animate-spin" />
                    <span>Finding nearest road...</span>
                  </div>
                )}
                {!sourceNodeLoading && sourceRoadNode && (
                  <div className="mt-1 flex items-center gap-1.5 text-[11px] text-emerald-600 dark:text-emerald-400 font-medium px-1">
                    <CheckCircle2 size={11} />
                    <span>
                      Road Node #{sourceRoadNode.nodeId} (
                      {sourceRoadNode.distance < 1
                        ? `${Math.round(sourceRoadNode.distance * 1000)}m`
                        : `${sourceRoadNode.distance.toFixed(1)} km`}{" "}
                      snap)
                    </span>
                  </div>
                )}
                {!sourceNodeLoading && sourceNodeError && (
                  <div className="mt-1 flex items-center gap-1.5 text-[11px] text-rose-600 dark:text-rose-400 font-medium px-1">
                    <AlertCircle size={11} />
                    <span>{sourceNodeError}</span>
                  </div>
                )}
              </div>

              {/* Destination input */}
              <div>
                <SearchInput
                  placeholder="Search destination..."
                  value={destinationText}
                  onChange={handleDestTextChange}
                  onClear={() => {
                    handleDestinationChange("");
                    destSearch.clearResults();
                  }}
                  onSelectResult={handleSelectDest}
                  icon={MapPin}
                  iconColor="text-rose-500"
                  results={destSearch.results}
                  loading={destSearch.loading}
                  searchError={destSearch.error}
                  aria-label="Destination"
                />

                {/* Subtle Destination Road Node status */}
                {destinationNodeLoading && (
                  <div className="mt-1 flex items-center gap-1.5 text-[11px] text-amber-600 dark:text-amber-400 font-medium px-1">
                    <Loader2 size={11} className="animate-spin" />
                    <span>Finding nearest road...</span>
                  </div>
                )}
                {!destinationNodeLoading && destinationRoadNode && (
                  <div className="mt-1 flex items-center gap-1.5 text-[11px] text-emerald-600 dark:text-emerald-400 font-medium px-1">
                    <CheckCircle2 size={11} />
                    <span>
                      Road Node #{destinationRoadNode.nodeId} (
                      {destinationRoadNode.distance < 1
                        ? `${Math.round(destinationRoadNode.distance * 1000)}m`
                        : `${destinationRoadNode.distance.toFixed(1)} km`}{" "}
                      snap)
                    </span>
                  </div>
                )}
                {!destinationNodeLoading && destinationNodeError && (
                  <div className="mt-1 flex items-center gap-1.5 text-[11px] text-rose-600 dark:text-rose-400 font-medium px-1">
                    <AlertCircle size={11} />
                    <span>{destinationNodeError}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Swap */}
            <div className="pt-1">
              <SwapButton onSwap={handleSwap} />
            </div>
          </div>

          {/* Panel-level validation / info messages */}
          {searchError && (
            <div
              role="alert"
              className="flex items-start gap-2 px-3 py-2.5 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800/50 rounded-xl text-xs font-medium text-rose-700 dark:text-rose-300 animate-fade-in"
            >
              <AlertCircle size={14} className="mt-px shrink-0" />
              <span>{searchError}</span>
            </div>
          )}

          {searchInfo && !searchError && (
            <div
              role="status"
              className="flex items-start gap-2 px-3 py-2.5 bg-primary/5 dark:bg-primary/10 border border-primary/20 dark:border-primary/30 rounded-xl text-xs font-medium text-primary dark:text-primary-light animate-fade-in"
            >
              <Info size={14} className="mt-px shrink-0" />
              <span>{searchInfo}</span>
            </div>
          )}

          {/* Non-blocking road node error notification if API fails */}
          {(sourceNodeError || destinationNodeError) && !searchError && (
            <div
              role="status"
              className="flex items-start gap-2 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 rounded-xl text-[11px] font-medium text-amber-700 dark:text-amber-300"
            >
              <AlertCircle size={13} className="mt-px shrink-0 text-amber-500" />
              <span>Road network lookup limited. Navigation search remains active.</span>
            </div>
          )}

          {/* Action row */}
          <div className="flex items-center justify-between">
            <CurrentLocationButton onSelect={handleUseCurrentLocation} />
            <ClearButton onClear={handleClearAll} />
          </div>

          {/* Routing Algorithm Selector — Sprint 5.3 */}
          <div className="flex flex-col gap-1.5 pt-2 border-t border-slate-100 dark:border-slate-800/80">
            <label className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Routing Algorithm
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setSelectedAlgorithm("astar")}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all border ${
                  selectedAlgorithm === "astar"
                    ? "bg-primary/10 border-primary text-primary dark:bg-primary/20 dark:text-primary-light shadow-sm"
                    : "bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${selectedAlgorithm === "astar" ? "bg-primary" : "bg-slate-400"}`} />
                A* Search
              </button>
              <button
                type="button"
                onClick={() => setSelectedAlgorithm("dijkstra")}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all border ${
                  selectedAlgorithm === "dijkstra"
                    ? "bg-primary/10 border-primary text-primary dark:bg-primary/20 dark:text-primary-light shadow-sm"
                    : "bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${selectedAlgorithm === "dijkstra" ? "bg-primary" : "bg-slate-400"}`} />
                Dijkstra
              </button>
            </div>
          </div>

          {/* Routing Mode Selector — Sprint 9B */}
          <div className="flex flex-col gap-1.5 pt-2 border-t border-slate-100 dark:border-slate-800/80">
            <label className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Routing Mode
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setSelectedRoutingMode("normal")}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all border ${
                  selectedRoutingMode === "normal"
                    ? "bg-emerald-500/10 border-emerald-500 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400 shadow-sm"
                    : "bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${selectedRoutingMode === "normal" ? "bg-emerald-500" : "bg-slate-400"}`} />
                Normal
              </button>
              <button
                type="button"
                onClick={() => setSelectedRoutingMode("traffic_aware")}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all border ${
                  selectedRoutingMode === "traffic_aware"
                    ? "bg-amber-500/10 border-amber-500 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400 shadow-sm"
                    : "bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${selectedRoutingMode === "traffic_aware" ? "bg-amber-500 animate-pulse" : "bg-slate-400"}`} />
                Traffic-Aware
              </button>
            </div>
          </div>

          {/* Search Route */}
          <SearchButton onClick={handleSearchRoute} isLoading={isSearching} />

          {/* Dev Diagnostic Panel */}
          <RoadNodeDiagnostic />
        </div>
      )}
    </div>
  );
};
