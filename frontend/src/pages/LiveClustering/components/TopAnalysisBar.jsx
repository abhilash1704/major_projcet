/**
 * TopAnalysisBar.jsx — Header Title & Top Control Bar for Live Vehicle Clustering Page
 *
 * Matching the exact mockup design:
 * Header: LIVE VEHICLE CLUSTERING [LIVE] | Real-Time Traffic Intelligence
 * Controls Bar: [ANALYSIS AREA Dropdown] [SEARCH BENGALURU AREA Input] [RADIUS 500m/1km/2km] [Analyze Live Area Button]
 */
import { useState, useCallback, useRef } from "react";
import { MapPin, Search, Play, ChevronDown } from "lucide-react";
import { MONITORING_AREAS, getAreasByCategory } from "../services/monitoringAreas";
import { searchBengaluruLocation } from "../services/areaSelectorService";
import { useLiveClustering } from "../context/LiveClusteringContext";

const RADIUS_OPTIONS = [
  { label: "500 m",  value: 500  },
  { label: "1 km",   value: 1000 },
  { label: "2 km",   value: 2000 },
];

export const TopAnalysisBar = () => {
  const { selectedArea, analysisRadiusMeters, analyzeArea, status } = useLiveClustering();

  const [selectedAreaId, setSelectedAreaId] = useState(selectedArea?.id || "silk_board");
  const [searchQuery, setSearchQuery]     = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [pickedResult, setPickedResult]   = useState(null);
  const [radius, setRadius]               = useState(analysisRadiusMeters || 1000);
  const debounceRef                       = useRef(null);

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

  const handleSearchInput = (e) => {
    const q = e.target.value;
    setSearchQuery(q);
    setPickedResult(null);

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
      } catch {
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

  const handleRadiusSelect = (newRadius) => {
    setRadius(newRadius);
    const areaToUse = pickedResult || MONITORING_AREAS.find((a) => a.id === selectedAreaId) || selectedArea;
    if (areaToUse) {
      analyzeArea(areaToUse, newRadius);
    }
  };

  const handleAnalyzeClick = useCallback(() => {
    const areaToUse = pickedResult || MONITORING_AREAS.find((a) => a.id === selectedAreaId) || selectedArea;
    if (areaToUse) {
      analyzeArea(areaToUse, radius);
    }
  }, [pickedResult, selectedAreaId, selectedArea, radius, analyzeArea]);

  const areasByCategory = getAreasByCategory();
  const isLoading = status === "STARTING_LIVE_ANALYSIS" || status === "LOADING";

  return (
    <div className="w-full bg-white dark:bg-surface-dark border-b border-slate-200 dark:border-slate-800 flex flex-col shadow-xs">
      
      {/* ── Top Header Row (Page Title) ─────────────────────────────────── */}
      <div className="px-5 py-3 flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-black text-slate-900 dark:text-white tracking-tight font-sans uppercase">
              LIVE VEHICLE CLUSTERING
            </h1>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-300">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              LIVE
            </span>
          </div>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-0.5">
            Real-Time Traffic Intelligence
          </p>
        </div>
      </div>

      {/* ── Control Bar Row ────────────────────────────────────────────── */}
      <div className="px-5 py-3 bg-slate-50/50 dark:bg-slate-900/30">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center gap-4">
          
          {/* 1. ANALYSIS AREA Dropdown */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">
              ANALYSIS AREA
            </label>
            <div className="relative flex items-center">
              <MapPin className="w-4 h-4 text-blue-600 dark:text-blue-400 absolute left-3 pointer-events-none z-10" />
              <select
                value={selectedAreaId}
                onChange={handlePresetChange}
                className="w-full text-sm font-semibold rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white pl-9 pr-8 py-2 appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500/30 cursor-pointer shadow-xs"
              >
                <option value="silk_board">Silk Board Junction</option>
                {Object.entries(areasByCategory).map(([category, areas]) => (
                  <optgroup key={category} label={category}>
                    {areas.map((a) => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 pointer-events-none" />
            </div>
          </div>

          {/* 2. SEARCH BENGALURU AREA Input */}
          <div className="flex-[1.5] min-w-[240px] relative">
            <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">
              SEARCH BENGALURU AREA
            </label>
            <div className="relative flex items-center">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={handleSearchInput}
                placeholder="Search area or landmark..."
                className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white pl-9 pr-9 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/30 shadow-xs"
              />
              {searchLoading && <span className="absolute right-3 text-xs text-slate-400 animate-spin">⟳</span>}
            </div>

            {/* Search Dropdown */}
            {searchResults.length > 0 && (
              <ul className="absolute z-50 left-0 right-0 mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-h-56 overflow-y-auto text-sm">
                {searchResults.map((r, i) => (
                  <li
                    key={i}
                    onClick={() => handlePickResult(r)}
                    className="px-3 py-2.5 hover:bg-blue-50 dark:hover:bg-slate-700/50 cursor-pointer text-slate-800 dark:text-slate-200 border-b border-slate-100 dark:border-slate-700/60 last:border-0 truncate"
                  >
                    <span className="font-semibold">{r.name}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* 3. RADIUS Buttons */}
          <div className="shrink-0">
            <label className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1">
              RADIUS
            </label>
            <div className="flex gap-1 p-1 bg-slate-200/60 dark:bg-slate-800 rounded-xl border border-slate-200/80 dark:border-slate-700/60">
              {RADIUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => handleRadiusSelect(opt.value)}
                  className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                    radius === opt.value
                      ? "bg-blue-600 text-white shadow-xs"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 4. Primary Button: Analyze Live Area */}
          <div className="shrink-0 pt-4 lg:pt-5">
            <button
              onClick={handleAnalyzeClick}
              disabled={isLoading}
              className="w-full lg:w-auto px-5 py-2 rounded-xl font-bold text-sm bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20 active:scale-95 transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>{isLoading ? "Analyzing..." : "Analyze Live Area"}</span>
            </button>
          </div>

        </div>
      </div>
    </div>
  );
};
