import { useState, useCallback, useRef, useEffect } from "react";
import { useNavigationEngineContext } from "../../navigation-engine/context/NavigationEngineContext";
import { useGeolocation } from "../../navigation-engine/hooks/useGeolocation";

/**
 * useSearchPanel — Phase 4.2
 *
 * Manages all state for the Location Search panel:
 *  - sourceText / destinationText  → display strings in the inputs
 *  - sourceLocation / destinationLocation → resolved coordinate objects (context)
 *  - isSearching → loading indicator for route action
 *  - searchError / searchInfo → panel-level messages
 *
 * Nominatim fetching is handled by useLocationSearch (separate hook).
 * This hook only owns state and actions, not API calls.
 */
export const useSearchPanel = () => {
  // ── shared context state (coordinate objects + persisted text) ─────────
  const {
    sourceText,
    setSourceText,
    destinationText,
    setDestinationText,
    currentLocation,
    setCurrentLocation,
    sourceLocation,
    setSourceLocation,
    destinationLocation,
    setDestinationLocation,
    sourceRoadNode,
    destinationRoadNode,
    activeRoute,
    selectedAlgorithm,
    setSelectedAlgorithm,
    selectedRoutingMode,
    setSelectedRoutingMode,
    calculateAndSetRoute,
    handleClearRoute,
  } = useNavigationEngineContext();

  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [searchInfo, setSearchInfo] = useState(null);

  // ── Restore searchInfo if an activeRoute was persisted across reloads ──
  useEffect(() => {
    if (activeRoute && !searchInfo && !searchError) {
      const distKm = activeRoute.total_distance_km ?? activeRoute.distance_km ?? 0;
      const mins = Math.round((activeRoute.total_travel_time_seconds ?? 0) / 60);
      const algoLabel = (activeRoute.algorithm || selectedAlgorithm) === "dijkstra" ? "Dijkstra" : "A* Search";
      const modeLabel = (activeRoute.routing_mode || selectedRoutingMode) === "traffic_aware" ? " (Traffic-Aware)" : "";
      setSearchInfo(
        `Route found: ${distKm.toFixed(1)} km · ~${mins} min via ${algoLabel}${modeLabel}`
      );
    }
  }, [activeRoute, selectedAlgorithm, selectedRoutingMode, searchInfo, searchError]);

  // ── geolocation (reuse existing hook — no second implementation) ───────
  const { getCurrentLocation, loading: geoLoading } = useGeolocation();

  // ── refs tracking latest values to avoid stale closures ───────────────
  const sourceTextRef = useRef(sourceText);
  const destinationTextRef = useRef(destinationText);
  const sourceLocationRef = useRef(sourceLocation);
  const destinationLocationRef = useRef(destinationLocation);

  useEffect(() => { sourceTextRef.current = sourceText; }, [sourceText]);
  useEffect(() => { destinationTextRef.current = destinationText; }, [destinationText]);
  useEffect(() => { sourceLocationRef.current = sourceLocation; }, [sourceLocation]);
  useEffect(() => { destinationLocationRef.current = destinationLocation; }, [destinationLocation]);

  // ── helpers ────────────────────────────────────────────────────────────
  const clearError = useCallback(() => {
    setSearchError(null);
    setSearchInfo(null);
  }, []);

  // ── text change handlers (clear resolved location when text changes) ───
  const handleSourceChange = useCallback(
    (text) => {
      setSourceText(text);
      // If user edits after a resolved selection, the location is now unresolved
      if (!text) setSourceLocation(null);
      clearError();
    },
    [setSourceLocation, clearError]
  );

  const handleDestinationChange = useCallback(
    (text) => {
      setDestinationText(text);
      if (!text) setDestinationLocation(null);
      clearError();
    },
    [setDestinationLocation, clearError]
  );

  // ── called by SearchPanel when a Nominatim result is selected ─────────
  const setSourceResolved = useCallback(
    (location) => {
      setSourceLocation(location);
      clearError();
    },
    [setSourceLocation, clearError]
  );

  const setDestinationResolved = useCallback(
    (location) => {
      setDestinationLocation(location);
      clearError();
    },
    [setDestinationLocation, clearError]
  );

  // ── Swap source ↔ destination (text + resolved location) ──────────────
  const handleSwap = useCallback(() => {
    clearError();
    const prevSrcText = sourceTextRef.current;
    const prevDestText = destinationTextRef.current;
    const prevSrcLoc = sourceLocationRef.current;
    const prevDestLoc = destinationLocationRef.current;

    setSourceText(prevDestText);
    setDestinationText(prevSrcText);
    setSourceLocation(prevDestLoc);
    setDestinationLocation(prevSrcLoc);
  }, [clearError, setSourceLocation, setDestinationLocation]);

  // ── Clear everything ───────────────────────────────────────────────────
  const handleClear = useCallback(() => {
    setSourceText("");
    setDestinationText("");
    setSourceLocation(null);
    setDestinationLocation(null);
    setIsSearching(false);
    clearError();
    if (handleClearRoute) {
      handleClearRoute();
    }
  }, [setSourceLocation, setDestinationLocation, clearError, handleClearRoute]);

  // ── Use current GPS location as source ────────────────────────────────
  const handleUseCurrentLocation = useCallback(() => {
    clearError();
    if (!navigator.geolocation) {
      setSearchError("Geolocation is not supported by your browser.");
      return;
    }
    getCurrentLocation(
      (coords) => {
        setCurrentLocation(coords);
        // Store as a resolved source location (lat/lng array)
        setSourceLocation(coords);
        setSourceText("My Current Location");
        clearError();
      },
      () => {
        setSearchError("Could not get your location. Please allow location access.");
      }
    );
  }, [getCurrentLocation, setCurrentLocation, setSourceLocation, clearError]);

  // ── Search Route — validate both fields and calculate route ─────────────
  const handleSearchRoute = useCallback(async () => {
    clearError();

    const srcText = sourceTextRef.current.trim();
    const destText = destinationTextRef.current.trim();
    const srcLoc = sourceLocationRef.current;
    const destLoc = destinationLocationRef.current;

    // Basic text validation
    if (!srcText && !destText) {
      setSearchError("Please enter a starting location and destination.");
      return;
    }
    if (!srcText) {
      setSearchError("Please enter a starting location.");
      return;
    }
    if (!destText) {
      setSearchError("Please enter a destination.");
      return;
    }

    // Both texts present — remind to select from suggestions if not resolved
    if (!srcLoc) {
      setSearchError("Please select a starting location from the suggestions.");
      return;
    }
    if (!destLoc) {
      setSearchError("Please select a destination from the suggestions.");
      return;
    }

    // Road node IDs must be resolved before calculating route
    if (!sourceRoadNode || !sourceRoadNode.nodeId) {
      setSearchError(
        "Source road node not resolved yet. Wait for the road network lookup to finish."
      );
      return;
    }
    if (!destinationRoadNode || !destinationRoadNode.nodeId) {
      setSearchError(
        "Destination road node not resolved yet. Wait for the road network lookup to finish."
      );
      return;
    }

    setIsSearching(true);
    setSearchInfo(null);

    try {
      // Pass coordinate objects so the backend can ensure_graph_for_points()
      // and load a unified NetworkX graph covering both endpoints.
      const srcCoords = sourceRoadNode
        ? { lat: sourceRoadNode.latitude, lon: sourceRoadNode.longitude }
        : null;
      const dstCoords = destinationRoadNode
        ? { lat: destinationRoadNode.latitude, lon: destinationRoadNode.longitude }
        : null;

      const route = await calculateAndSetRoute(
        sourceRoadNode.nodeId,
        destinationRoadNode.nodeId,
        srcCoords,
        dstCoords,
        selectedAlgorithm,
        selectedRoutingMode,
        srcText,
        destText
      );
      if (route) {
        const distKm = route.total_distance_km ?? 0;
        const mins = Math.round((route.total_travel_time_seconds ?? 0) / 60);
        const algoLabel = route.algorithm === "dijkstra" || selectedAlgorithm === "dijkstra" ? "Dijkstra" : "A* Search";
        const modeLabel = route.routing_mode === "traffic_aware" ? " (Traffic-Aware)" : "";
        setSearchInfo(
          `Route found: ${distKm.toFixed(1)} km · ~${mins} min via ${algoLabel}${modeLabel}`
        );
      } else {
        setSearchError("No route could be calculated between the selected points.");
      }
    } catch (err) {
      setSearchError(err.message || "Route calculation failed.");
    } finally {
      setIsSearching(false);
    }
  }, [clearError, sourceRoadNode, destinationRoadNode, selectedAlgorithm, selectedRoutingMode, calculateAndSetRoute]);

  return {
    // text
    sourceText,
    destinationText,
    // locations (from context)
    sourceLocation,
    destinationLocation,
    currentLocation,
    // status
    isSearching,
    searchError,
    searchInfo,
    geoLoading,
    // actions
    handleSourceChange,
    handleDestinationChange,
    setSourceResolved,
    setDestinationResolved,
    handleSwap,
    handleClear,
    handleUseCurrentLocation,
    handleSearchRoute,
  };
};
