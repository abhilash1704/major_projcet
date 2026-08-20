/**
 * AreaSelector.jsx — Live Clustering Phase 4
 *
 * UI for selecting the Bengaluru analysis area:
 *   - Preset dropdown (50 monitoring areas, grouped by category)
 *   - Search box (Nominatim geocoding via backend)
 *   - Radius selector (500m / 1km / 2km)
 *   - "Analyze Live Area" button
 *
 * DOES NOT: call A*, Dijkstra, modify NavigationEngineContext, or create routes.
 */
import { useState, useCallback, useRef } from "react";
import { MONITORING_AREAS, getAreasByCategory } from "../services/monitoringAreas";
import { searchBengaluruLocation } from "../services/areaSelectorService";
import { useLiveClustering } from "../context/LiveClusteringContext";

const RADIUS_OPTIONS = [
  { label: "500 m",  value: 500  },
  { label: "1 km",   value: 1000 },
  { label: "2 km",   value: 2000 },
];

export const AreaSelector = () => {
  const { analyzeArea, analysisStatus } = useLiveClustering();

  const [mode, setMode]                   = useState("preset"); // "preset" | "search"
  const [selectedAreaId, setSelectedAreaId] = useState("");
  const [searchQuery, setSearchQuery]     = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError]     = useState(null);
  const [pickedResult, setPickedResult]   = useState(null); // chosen search result
  const [radius, setRadius]               = useState(1000);
  const debounceRef                       = useRef(null);

  // ── Preset selection ────────────────────────────────────────────────────────
  const handlePresetChange = (e) => {
    const areaId = e.target.value;
    setSelectedAreaId(areaId);
    setPickedResult(null);
    if (areaId) {
      const found = MONITORING_AREAS.find((a) => a.id === areaId);
      if (found) {
        analyzeArea({ ...found, source: "preset" }, radius);
      }
    }
  };

  // ── Search (debounced) ──────────────────────────────────────────────────────
  const handleSearchInput = (e) => {
    const q = e.target.value;
    setSearchQuery(q);
    setPickedResult(null);
    setSearchError(null);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q.trim() || q.trim().length < 2) {
      setSearchResults([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const results = await searchBengaluruLocation(q);
        setSearchResults(results);
        if (results.length === 0) setSearchError("No locations found in Bengaluru.");
      } catch (err) {
        setSearchError(err.message ?? "Search failed.");
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 450);
  };

  const handlePickResult = (result) => {
    setPickedResult(result);
    setSearchQuery(result.name);
    setSearchResults([]);
    analyzeArea(result, radius);
  };

  // ── Analyze ─────────────────────────────────────────────────────────────────
  const getSelectedArea = useCallback(() => {
    if (mode === "preset") {
      if (!selectedAreaId) return null;
      const found = MONITORING_AREAS.find((a) => a.id === selectedAreaId);
      return found ? { ...found, source: "preset" } : null;
    } else {
      return pickedResult; // already has { name, latitude, longitude, source: "search" }
    }
  }, [mode, selectedAreaId, pickedResult]);

  const handleAnalyze = useCallback(() => {
    const area = getSelectedArea();
    if (!area) return;
    analyzeArea(area, radius);
  }, [getSelectedArea, radius, analyzeArea]);

  const handleRadiusSelect = (newRadius) => {
    setRadius(newRadius);
    const area = getSelectedArea();
    if (area) {
      analyzeArea(area, newRadius);
    }
  };

  const areasByCategory = getAreasByCategory();
  const isLoading = analysisStatus === "LOADING";

  return (
    <div className="bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider">
          Analysis Area
        </span>
        {/* Mode toggle */}
        <div className="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 text-xs">
          <button
            onClick={() => setMode("preset")}
            className={`px-3 py-1 rounded-md font-medium transition-colors ${
              mode === "preset"
                ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm"
                : "text-slate-500 dark:text-slate-400 hover:text-slate-700"
            }`}
          >
            Preset
          </button>
          <button
            onClick={() => setMode("search")}
            className={`px-3 py-1 rounded-md font-medium transition-colors ${
              mode === "search"
                ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm"
                : "text-slate-500 dark:text-slate-400 hover:text-slate-700"
            }`}
          >
            Search
          </button>
        </div>
      </div>

      {/* Preset mode */}
      {mode === "preset" && (
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
            Monitoring Area
          </label>
          <select
            id="area-preset-select"
            value={selectedAreaId}
            onChange={handlePresetChange}
            className="w-full text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            <option value="">— Select a monitoring area —</option>
            {Object.entries(areasByCategory).map(([category, areas]) => (
              <optgroup key={category} label={category}>
                {areas.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
      )}

      {/* Search mode */}
      {mode === "search" && (
        <div className="relative">
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
            Search Bengaluru Location
          </label>
          <div className="relative">
            <input
              id="area-search-input"
              type="text"
              value={searchQuery}
              onChange={handleSearchInput}
              placeholder="e.g. Silk Board, Whitefield…"
              className="w-full text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            <span className="absolute right-2.5 top-2.5 text-slate-400 text-sm">
              {searchLoading ? "⟳" : "🔍"}
            </span>
          </div>
          {/* Results dropdown */}
          {searchResults.length > 0 && (
            <ul className="absolute z-50 mt-1 w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg overflow-hidden text-sm">
              {searchResults.map((r, i) => (
                <li
                  key={i}
                  onClick={() => handlePickResult(r)}
                  className="px-3 py-2 hover:bg-primary/10 cursor-pointer text-slate-700 dark:text-slate-300 border-b border-slate-100 dark:border-slate-700 last:border-0 truncate"
                  title={r.full_name}
                >
                  📍 {r.name}
                  <span className="text-xs text-slate-400 ml-1">{r.latitude.toFixed(4)}, {r.longitude.toFixed(4)}</span>
                </li>
              ))}
            </ul>
          )}
          {searchError && !searchLoading && (
            <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">{searchError}</p>
          )}
          {pickedResult && (
            <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-1">
              <span>✓</span> {pickedResult.name} selected
            </p>
          )}
        </div>
      )}

      {/* Radius selector */}
      <div>
        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
          Analysis Radius
        </label>
        <div className="flex gap-2">
          {RADIUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => handleRadiusSelect(opt.value)}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                radius === opt.value
                  ? "bg-primary text-white border-primary shadow-sm"
                  : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-primary/50"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Analyze button */}
      <button
        id="btn-analyze-area"
        onClick={handleAnalyze}
        disabled={isLoading || (!selectedAreaId && !pickedResult)}
        className="w-full py-2.5 px-4 rounded-xl font-semibold text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed
          bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500
          shadow-md shadow-indigo-500/20 active:scale-95"
      >
        {isLoading ? "⟳ Analyzing…" : "Analyze Live Area"}
      </button>
    </div>
  );
};
