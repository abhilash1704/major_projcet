import { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import { ENGINE_CONFIG } from "../constants/engineConstants";
import { layerService } from "../services/layerService";
import { overlayService } from "../services/overlayService";
import { findNearestRoadNode, calculateRoute, compareAlgorithms, setActiveRoute as backendSetActiveRoute, rejectReroute as backendRejectReroute, fetchAlternativeRoutes } from "../../../services/roadNetworkService";
import {
  generateVehicles,
  updateSimulation,
  clearSimulation,
  startSimulation,
  pauseSimulation,
  resumeSimulation,
} from "../../../services/vehicleService";

export const NavigationContext = createContext(null);

const SIMULATION_INTERVAL_MS = 1000; // 1 second
const SIMULATION_DELTA_SECONDS = 1;

/**
 * Helper to safely extract numeric { lat, lon } from location object or [lat, lon] array.
 */
function extractCoords(loc) {
  if (!loc) return null;
  if (Array.isArray(loc)) {
    const lat = Number(loc[0]);
    const lon = Number(loc[1]);
    return isFinite(lat) && isFinite(lon) && lat !== 0 && lon !== 0 ? { lat, lon } : null;
  }
  const lat = Number(loc.latitude ?? loc.lat);
  const lon = Number(loc.longitude ?? loc.lng);
  return isFinite(lat) && isFinite(lon) && lat !== 0 && lon !== 0 ? { lat, lon } : null;
}

export const NavigationProvider = ({ children }) => {
  const [mapInstance, setMapInstance] = useState(null);
  const [center, setCenter] = useState(ENGINE_CONFIG.DEFAULT_CENTER);
  const [zoom, setZoom] = useState(ENGINE_CONFIG.DEFAULT_ZOOM);

  // State required for Phase 3 & 4
  const [currentLocation, setCurrentLocation] = useState(null);
  const [sourceText, setSourceTextState] = useState(() => {
    return localStorage.getItem("rf_source_text") || "";
  });
  const [destinationText, setDestinationTextState] = useState(() => {
    return localStorage.getItem("rf_destination_text") || "";
  });
  const [sourceLocation, setSourceLocationState] = useState(() => {
    try {
      const saved = localStorage.getItem("rf_source_location");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [destinationLocation, setDestinationLocationState] = useState(() => {
    try {
      const saved = localStorage.getItem("rf_destination_location");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const setSourceText = useCallback((val) => {
    setSourceTextState(val);
    if (val) localStorage.setItem("rf_source_text", val);
    else localStorage.removeItem("rf_source_text");
  }, []);

  const setDestinationText = useCallback((val) => {
    setDestinationTextState(val);
    if (val) localStorage.setItem("rf_destination_text", val);
    else localStorage.removeItem("rf_destination_text");
  }, []);

  const setSourceLocation = useCallback((val) => {
    setSourceLocationState(val);
    if (val) localStorage.setItem("rf_source_location", JSON.stringify(val));
    else localStorage.removeItem("rf_source_location");
  }, []);

  const setDestinationLocation = useCallback((val) => {
    setDestinationLocationState(val);
    if (val) localStorage.setItem("rf_destination_location", JSON.stringify(val));
    else localStorage.removeItem("rf_destination_location");
  }, []);

  // Sprint 5.4 — Road Network Node state
  const [sourceRoadNode, setSourceRoadNode] = useState(null);
  const [destinationRoadNode, setDestinationRoadNode] = useState(null);
  const [sourceNodeLoading, setSourceNodeLoading] = useState(false);
  const [destinationNodeLoading, setDestinationNodeLoading] = useState(false);
  const [sourceNodeError, setSourceNodeError] = useState(null);
  const [destinationNodeError, setDestinationNodeError] = useState(null);

  // Sprint 5.5 — Active route state
  const [activeRoute, setActiveRouteState] = useState(() => {
    try {
      const saved = localStorage.getItem("rf_active_route");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });   // full route object from /api/routes/calculate
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState(null);
  const [selectedAlgorithm, setSelectedAlgorithmState] = useState(() => {
    return localStorage.getItem("rf_selected_algorithm") || "astar";
  });
  const [selectedRoutingMode, setSelectedRoutingModeState] = useState(() => {
    return localStorage.getItem("rf_selected_routing_mode") || "normal";
  });

  const setActiveRoute = useCallback((val) => {
    setActiveRouteState(val);
    if (val) localStorage.setItem("rf_active_route", JSON.stringify(val));
    else localStorage.removeItem("rf_active_route");
  }, []);

  const setSelectedAlgorithm = useCallback((val) => {
    setSelectedAlgorithmState(val);
    localStorage.setItem("rf_selected_algorithm", val);
  }, []);

  const setSelectedRoutingMode = useCallback((val) => {
    setSelectedRoutingModeState(val);
    localStorage.setItem("rf_selected_routing_mode", val);
  }, []);

  // Sprint 10, 11 & 11C & High-Traffic Alternative Engine State
  const [comparisonData, setComparisonData] = useState(null);
  const [rerouteRecommendation, setRerouteRecommendation] = useState(null);
  const [previewRoute, setPreviewRoute] = useState(null);
  const [isRouteSwitching, setIsRouteSwitching] = useState(false);
  const [routeSwitchError, setRouteSwitchError] = useState(null);
  const [isAlternativeCalculating, setIsAlternativeCalculating] = useState(false);

  // ── On-Demand Alternative Routes (AlternativeRoutesCard) ─────────────────
  const [alternativeRoutes, setAlternativeRoutes] = useState([]);
  const [isGeneratingAlternatives, setIsGeneratingAlternatives] = useState(false);
  const [alternativeGenerationError, setAlternativeGenerationError] = useState(null);
  const [simulationStartedAt, setSimulationStartedAt] = useState(null); // timestamp when sim became RUNNING
  const [alternativeAnalysisStatus, setAlternativeAnalysisStatus] = useState("idle"); // idle | waiting | analyzing | done | error
  const alternativeRouteRequestIdRef = useRef(0);
  const analysisTimerRef = useRef(null);  // 5-second delay timer

  // Edge-trigger and stale result protection refs
  const previousTrafficLevelRef = useRef("LOW");
  const alternativeRequestIdRef = useRef(0);


  // Development-only diagnostic mode flag
  const [isDebugMode, setIsDebugMode] = useState(false);

  const [visibleLayers, setVisibleLayers] = useState(layerService.getDefaultLayers());
  const [visibleOverlays, setVisibleOverlays] = useState(overlayService.getDefaultOverlays());
  const [trafficMode, setTrafficMode] = useState("normal"); // 'normal' | 'live' | 'predictive'

  // ── Sprint 6.5 & 6.6B — Traffic Hotspots State ─────────────────────────────────
  const [hotspotsData, setHotspotsData] = useState(null);
  const [hotspotsError, setHotspotsError] = useState(null);
  const [isTrafficUpdating, setIsTrafficUpdating] = useState(false);
  const [trafficLastUpdated, setTrafficLastUpdated] = useState(null);

  // ── Sprint 8 — Cluster Layer State ────────────────────────────────────────────
  const [clustersData, setClustersData] = useState(null);

  // ── Sprint 4.4 — Vehicle Simulation State ──────────────────────────────
  const [vehicles, setVehicles] = useState([]);
  const [simulationStatus, setSimulationStatus] = useState("idle"); // idle | starting | running | paused | error
  const [simulationError, setSimulationError] = useState(null);
  const [lastUpdateTime, setLastUpdateTime] = useState(null);

  // Single ref-controlled interval — prevents duplicate timers
  const simulationIntervalRef = useRef(null);

  // Compatibility alias for userLocation
  const userLocation = currentLocation;
  const setUserLocation = setCurrentLocation;

  // ── Simulation: cleanup on unmount & initial backend wipe ────────────────
  useEffect(() => {
    // Purge any leftover backend simulation vehicles from crashed/prior server runs
    clearSimulation().catch((err) => {
      console.warn("Initial backend simulation cleanup notice:", err.message);
    });
    return () => {
      if (simulationIntervalRef.current) {
        clearInterval(simulationIntervalRef.current);
        simulationIntervalRef.current = null;
      }
    };
  }, []);

  // ── Sprint 6.5 & 6.6B & Sprint 8: Traffic Polling (hotspots + clusters) ──────
  useEffect(() => {
    // Poll only when: traffic layer active AND vehicles exist in simulation
    const shouldPoll = visibleLayers.traffic && vehicles && vehicles.length > 0;
    const clusterPoll = visibleLayers.cluster && vehicles && vehicles.length > 0;
    
    // Always poll active route to check for reroute recommendation if a route is active
    const shouldCheckReroute = !!activeRoute;

    if (!shouldPoll && !clusterPoll && !shouldCheckReroute) {
      setHotspotsData(null);
      setHotspotsError(null);
      setClustersData(null);
      setRerouteRecommendation(null);
      setIsTrafficUpdating(false);
      return;
    }

    let isMounted = true;
    let pollTimer = null;
    let abortHotspot = null;
    let abortCluster = null;

    const baseUrl = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:5000";

    const fetchTrafficData = async () => {
      // Abort any in-flight requests
      if (abortHotspot) abortHotspot.abort();
      if (abortCluster) abortCluster.abort();
      abortHotspot = new AbortController();
      abortCluster = new AbortController();

      if (isMounted) setIsTrafficUpdating(true);

      // Fire both requests concurrently using Promise.allSettled
      const promises = [];
      if (shouldPoll) {
        promises.push(
          fetch(`${baseUrl}/api/traffic-intelligence/hotspots`, { signal: abortHotspot.signal })
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
        );
      } else {
        promises.push(Promise.resolve(null));
      }

      if (clusterPoll) {
        promises.push(
          fetch(`${baseUrl}/api/traffic-intelligence/clusters`, { signal: abortCluster.signal })
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
        );
      } else {
        promises.push(Promise.resolve(null));
      }

      const [hotspotResult, clusterResult] = await Promise.allSettled(promises);

      if (!isMounted) return;

      // Handle hotspot result
      if (hotspotResult.status === 'fulfilled' && hotspotResult.value) {
        setHotspotsData(hotspotResult.value);
        setHotspotsError(null);
        setTrafficLastUpdated(new Date());
      } else if (hotspotResult.status === 'rejected') {
        const err = hotspotResult.reason;
        if (err?.name !== 'AbortError') {
          setHotspotsError("Failed to fetch hotspots");
        }
      }

      // Handle cluster result
      if (clusterResult.status === 'fulfilled' && clusterResult.value) {
        setClustersData(clusterResult.value);
      } else if (clusterResult.status === 'rejected') {
        const err = clusterResult.reason;
        if (err?.name !== 'AbortError') {
          setClustersData(null);
        }
      }

      if (isMounted && shouldCheckReroute && simulationStatus === 'running') {
        fetch(`${baseUrl}/api/routes/active`, { signal: abortHotspot.signal })
          .then(r => r.ok ? r.json() : null)
          .then(async (data) => {
            if (isMounted && data && data.success && data.reroute_recommendation) {
              const rec = data.reroute_recommendation;
              if (!isAlternativeCalculating && rec.status && rec.status !== "ERROR") {
                setRerouteRecommendation(rec);
              }
            }
          })
          .catch(() => {});
      }

      if (isMounted) setIsTrafficUpdating(false);
    };

    fetchTrafficData();
    pollTimer = setInterval(fetchTrafficData, 5000);

    return () => {
      isMounted = false;
      if (abortHotspot) abortHotspot.abort();
      if (abortCluster) abortCluster.abort();
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [visibleLayers.traffic, visibleLayers.cluster, vehicles.length, simulationStatus, activeRoute, isAlternativeCalculating]);

  // ── High-Traffic Alternative Route User Trigger ─────────────────────────
  const handleGenerateAlternativeRoutes = useCallback(async () => {
    if (!activeRoute || isAlternativeCalculating) return;

    const srcId = activeRoute.source_node_id || activeRoute.source_node;
    const dstId = activeRoute.target_node_id || activeRoute.destination_node;
    if (!srcId || !dstId) return;

    const reqId = ++alternativeRequestIdRef.current;
    setIsAlternativeCalculating(true);

    const currDist = activeRoute.total_distance_km || activeRoute.distance_km || 0;
    const currEta = Math.round((activeRoute.total_travel_time_seconds || 0) / 60);

    setRerouteRecommendation({
      status: "CALCULATING",
      reason: "HIGH traffic detected on active route. Finding best alternatives...",
      current_route: {
        distance_km: currDist,
        eta_minutes: currEta,
        traffic_level: "HIGH",
        traffic_cost: activeRoute.traffic_cost || 0
      },
      alternatives: []
    });

    try {
      const data = await fetchAlternativeRoutes(srcId, dstId, activeRoute, "HIGH", 2, reqId);

      // Stale Result Protection Check
      if (alternativeRequestIdRef.current !== reqId) {
        console.log("[ALT_ENGINE] Discarded stale result", reqId);
        return;
      }

      setIsAlternativeCalculating(false);

      if (data && (data.success || data.status === "success" || data.status === "partial")) {
        const alts = data.alternatives || [];
        if (alts.length > 0) {
          setRerouteRecommendation({
            status: "REROUTE_AVAILABLE",
            reason: `HIGH traffic detected. Found ${alts.length} alternative route(s).`,
            current_route: data.current_route || {
              distance_km: currDist,
              eta_minutes: currEta,
              traffic_level: "HIGH"
            },
            alternative_routes: alts,
            alternatives: alts,
            generation_time_ms: data.generation_time_ms || data.execution_time_ms
          });
        } else {
          setRerouteRecommendation({
            status: "NO_BETTER_ROUTE",
            reason: "No suitable alternative route found.",
            current_route: data.current_route || {
              distance_km: currDist,
              eta_minutes: currEta,
              traffic_level: "HIGH"
            },
            alternative_routes: [],
            alternatives: []
          });
        }
      } else if (data && data.reason === "timeout") {
        setRerouteRecommendation({
          status: "TIMEOUT",
          reason: "Route generation timed out.",
          current_route: {
            distance_km: currDist,
            eta_minutes: currEta,
            traffic_level: "HIGH"
          },
          alternative_routes: [],
          alternatives: []
        });
      } else {
        setRerouteRecommendation({
          status: "ERROR",
          reason: data?.message || "Failed to calculate alternative routes.",
          current_route: {
            distance_km: currDist,
            eta_minutes: currEta,
            traffic_level: "HIGH"
          },
          alternative_routes: [],
          alternatives: []
        });
      }
    } catch (err) {
      console.error("[ALT_ENGINE] Alternative route calculation error:", err);
      if (alternativeRequestIdRef.current === reqId) {
        setIsAlternativeCalculating(false);
        setRerouteRecommendation({
          status: "ERROR",
          reason: err.message || "Failed to generate alternative routes.",
          current_route: {
            distance_km: currDist,
            eta_minutes: currEta,
            traffic_level: "HIGH"
          },
          alternative_routes: [],
          alternatives: []
        });
      }
    }
  }, [activeRoute, isAlternativeCalculating]);

  // ── On-Demand Alternative Route Generation (AlternativeRoutesCard) ───────
  const handleGenerateAlternatives = useCallback(async () => {
    if (!activeRoute || isGeneratingAlternatives) return;

    const srcId = activeRoute.source_node_id || activeRoute.source_node;
    const dstId = activeRoute.target_node_id || activeRoute.destination_node;
    if (!srcId || !dstId) return;

    const reqId = ++alternativeRouteRequestIdRef.current;
    setIsGeneratingAlternatives(true);
    setAlternativeGenerationError(null);
    setAlternativeRoutes([]);
    setAlternativeAnalysisStatus("analyzing");

    // 20-second hard frontend timeout
    let timeoutId = null;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => reject(new Error("TIMEOUT")), 20000);
    });

    try {
      const data = await Promise.race([
        fetchAlternativeRoutes(srcId, dstId, activeRoute, "HIGH", 2, reqId),
        timeoutPromise
      ]);
      clearTimeout(timeoutId);

      // Stale request protection
      if (alternativeRouteRequestIdRef.current !== reqId) return;

      setIsGeneratingAlternatives(false);

      if (data && (data.success || data.status === "success" || data.status === "partial")) {
        const alts = data.alternatives || [];
        setAlternativeRoutes(alts);
        if (alts.length === 0) {
          setAlternativeGenerationError("No suitable alternative routes found.");
          setAlternativeAnalysisStatus("done");
        } else {
          setAlternativeAnalysisStatus("done");
        }
      } else {
        setAlternativeGenerationError(data?.message || "Failed to generate alternative routes.");
        setAlternativeAnalysisStatus("error");
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (alternativeRouteRequestIdRef.current !== reqId) return;
      setIsGeneratingAlternatives(false);
      if (err.message === "TIMEOUT") {
        setAlternativeGenerationError("Alternative route generation timed out. Current route is still active.");
      } else {
        setAlternativeGenerationError(err.message || "Failed to generate alternative routes.");
      }
      setAlternativeAnalysisStatus("error");
    }
  }, [activeRoute, isGeneratingAlternatives]);

  // ── Auto-trigger alternative analysis 5s after simulation starts ─────────
  useEffect(() => {
    // Clear any existing timer when deps change
    if (analysisTimerRef.current) {
      clearTimeout(analysisTimerRef.current);
      analysisTimerRef.current = null;
    }

    // Only auto-trigger when simulation is RUNNING, route exists, not already generating/done
    if (
      simulationStatus !== "running" ||
      !activeRoute ||
      isGeneratingAlternatives ||
      (alternativeRoutes && alternativeRoutes.length > 0)
    ) {
      return;
    }

    // Record that simulation started (for UI display)
    setSimulationStartedAt(Date.now());
    setAlternativeAnalysisStatus("waiting");

    // Start 5-second delayed auto-analysis
    analysisTimerRef.current = setTimeout(() => {
      analysisTimerRef.current = null;
      // Re-check conditions (via ref and state snapshot)
      handleGenerateAlternatives();
    }, 5000);

    return () => {
      if (analysisTimerRef.current) {
        clearTimeout(analysisTimerRef.current);
        analysisTimerRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [simulationStatus, activeRoute]);


  // ── Route Calculation — Sprint 5.3 / 5.5 ───────────────────────────────────
  // Accepts optional coordinate objects and algorithm selection ('astar' | 'dijkstra')
  const calculateAndSetRoute = useCallback(async (
    srcNodeId, dstNodeId,
    srcCoords = null,   // { lat, lon } or null
    dstCoords = null,   // { lat, lon } or null
    algorithm = "astar",
    routingMode = "normal",
    srcName = null,
    dstName = null
  ) => {
    if (!srcNodeId || !dstNodeId) return null;
    setRouteLoading(true);
    setRouteError(null);

    try {
      const route = await calculateRoute(srcNodeId, dstNodeId, srcCoords, dstCoords, algorithm, routingMode, srcName, dstName);
      if (route) {
        // Step 9 — Only replace existing route after both endpoints resolve and new route is calculated
        setActiveRoute(route);

        // Invalidate stale alternative calculations & reset traffic transition state
        alternativeRequestIdRef.current++;
        alternativeRouteRequestIdRef.current++;
        previousTrafficLevelRef.current = "LOW";
        setIsAlternativeCalculating(false);
        setRerouteRecommendation(null);
        setPreviewRoute(null);
        // Clear on-demand alternative routes when route changes
        setAlternativeRoutes([]);
        setAlternativeGenerationError(null);
        setSimulationStartedAt(null);
        setAlternativeAnalysisStatus("idle");
        if (analysisTimerRef.current) { clearTimeout(analysisTimerRef.current); analysisTimerRef.current = null; }

        // Perform background algorithm comparison without overriding active route
        compareAlgorithms(srcNodeId, dstNodeId, srcCoords, dstCoords, routingMode)
          .then((data) => setComparisonData(data))
          .catch((err) => console.warn("Background algorithm comparison notice:", err.message));
      }
      return route;
    } catch (err) {
      console.error("Route calculation failed:", err.message);
      setRouteError(err.message || "Route calculation failed.");
      return null;
    } finally {
      setRouteLoading(false);
    }
  }, []);

  // ── Route Clear — STATE 7 ───────────────────────────────────────────────
  const handleClearRoute = useCallback(async () => {
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current);
      simulationIntervalRef.current = null;
    }
    // Invalidate stale alternative calculations & reset traffic transition state
    alternativeRequestIdRef.current++;
    alternativeRouteRequestIdRef.current++;
    previousTrafficLevelRef.current = "LOW";
    setIsAlternativeCalculating(false);

    setSourceText("");
    setDestinationText("");
    setSourceLocation(null);
    setDestinationLocation(null);
    setActiveRoute(null);
    setRouteError(null);
    setVehicles([]);
    setSimulationStatus("idle");
    setHotspotsData(null);
    setHotspotsError(null);
    setClustersData(null);
    setComparisonData(null);
    setRerouteRecommendation(null);
    setPreviewRoute(null);
    // Clear on-demand alternative routes state
    setAlternativeRoutes([]);
    setAlternativeGenerationError(null);
    setSimulationStartedAt(null);
    setAlternativeAnalysisStatus("idle");
    if (analysisTimerRef.current) { clearTimeout(analysisTimerRef.current); analysisTimerRef.current = null; }
    try {
      await clearSimulation();
    } catch (err) {
      console.warn("Clear simulation on route clear failed:", err.message);
    }
  }, [setSourceText, setDestinationText, setSourceLocation, setDestinationLocation, setActiveRoute]);

  // ── Simulation: Generate Vehicles (route-aware) ─────────────────────────────
  const handleGenerateVehicles = useCallback(async (count = 100) => {
    try {
      setSimulationStatus("starting");
      setSimulationError(null);
      const result = await generateVehicles(count);
      if (result && result.vehicles) {
        setVehicles(result.vehicles);
        // Clear any stale alternatives from a previous run
        setAlternativeRoutes([]);
        setAlternativeGenerationError(null);
        setAlternativeAnalysisStatus("idle");
      }
      setSimulationStatus("idle");
    } catch (err) {
      console.error("Vehicle generation failed:", err.message);
      setSimulationError(err.message || "Vehicle generation failed.");
      setSimulationStatus("error");
    }
  }, []);

  // ── Simulation: Single tick ─────────────────────────────────────────────
  const runSimulationTick = useCallback(async () => {
    try {
      const result = await updateSimulation(SIMULATION_DELTA_SECONDS);
      if (result && result.vehicles) {
        setVehicles(result.vehicles);
      }
      setLastUpdateTime(new Date());
    } catch (err) {
      console.error("Simulation update failed:", err.message);
      setSimulationError(err.message || "Simulation update failed.");
      setSimulationStatus("error");
      if (simulationIntervalRef.current) {
        clearInterval(simulationIntervalRef.current);
        simulationIntervalRef.current = null;
      }
    }
  }, []);

  // ── Simulation: Start ───────────────────────────────────────────────────
  const handleStartSimulation = useCallback(async () => {
    // Prevent duplicate timers — idempotent
    if (simulationIntervalRef.current) return;
    if (vehicles.length === 0) {
      setSimulationError("No vehicles. Generate vehicles first.");
      return;
    }
    
    try {
      await startSimulation();
      setSimulationError(null);
      setSimulationStatus("running");
      // Run first tick immediately then start interval
      await runSimulationTick();
      simulationIntervalRef.current = setInterval(runSimulationTick, SIMULATION_INTERVAL_MS);
    } catch (err) {
      console.error("Failed to start simulation backend:", err.message);
      setSimulationError(err.message || "Failed to start simulation backend.");
      setSimulationStatus("error");
    }
  }, [vehicles.length, runSimulationTick]);

  // ── Simulation: Pause ───────────────────────────────────────────────────
  const handlePauseSimulation = useCallback(async () => {
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current);
      simulationIntervalRef.current = null;
    }
    try {
      await pauseSimulation();
      setSimulationStatus("paused");
    } catch (err) {
      console.error("Failed to pause simulation backend:", err.message);
    }
  }, []);

  // ── Simulation: Resume ──────────────────────────────────────────────────
  const handleResumeSimulation = useCallback(async () => {
    // Prevent duplicate timers — idempotent
    if (simulationIntervalRef.current) return;
    if (vehicles.length === 0) return;
    
    try {
      await resumeSimulation();
      setSimulationStatus("running");
      setSimulationError(null);
      simulationIntervalRef.current = setInterval(runSimulationTick, SIMULATION_INTERVAL_MS);
    } catch (err) {
      console.error("Failed to resume simulation backend:", err.message);
      setSimulationError(err.message || "Failed to resume simulation.");
      setSimulationStatus("error");
    }
  }, [vehicles.length, runSimulationTick]);

  // ── Simulation: Reset ───────────────────────────────────────────────────
  const handleResetSimulation = useCallback(async () => {
    // Stop interval first
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current);
      simulationIntervalRef.current = null;
    }
    setSimulationStatus("idle");
    setSimulationError(null);
    setLastUpdateTime(null);
    setVehicles([]);
    setHotspotsData(null);
    setHotspotsError(null);
    setClustersData(null);
    // Reset on-demand alternative routes state
    alternativeRouteRequestIdRef.current++;
    setAlternativeRoutes([]);
    setAlternativeGenerationError(null);
    setSimulationStartedAt(null);
    setAlternativeAnalysisStatus("idle");
    if (analysisTimerRef.current) { clearTimeout(analysisTimerRef.current); analysisTimerRef.current = null; }
    try {
      await clearSimulation();
    } catch (err) {
      console.warn("Clear simulation backend call failed:", err.message);
    }
  }, []);

  // ── Effect: Resolve Source Road Node on sourceLocation change ──────────
  useEffect(() => {
    const coords = extractCoords(sourceLocation);
    if (!coords) {
      setSourceRoadNode(null);
      setSourceNodeError(null);
      setSourceNodeLoading(false);
      return;
    }

    let isMounted = true;
    setSourceRoadNode(null);
    setSourceNodeLoading(true);
    setSourceNodeError(null);

    findNearestRoadNode(coords.lat, coords.lon)
      .then((node) => {
        if (isMounted) {
          setSourceRoadNode(node);
          setSourceNodeLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.warn("Source road node resolution error:", err.message);
          setSourceRoadNode(null);
          setSourceNodeError(err.message);
          setSourceNodeLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [sourceLocation]);

  // ── Effect: Resolve Destination Road Node on destinationLocation change ─
  useEffect(() => {
    const coords = extractCoords(destinationLocation);
    if (!coords) {
      setDestinationRoadNode(null);
      setDestinationNodeError(null);
      setDestinationNodeLoading(false);
      return;
    }

    let isMounted = true;
    setDestinationRoadNode(null);
    setDestinationNodeLoading(true);
    setDestinationNodeError(null);

    findNearestRoadNode(coords.lat, coords.lon)
      .then((node) => {
        if (isMounted) {
          setDestinationRoadNode(node);
          setDestinationNodeLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.warn("Destination road node resolution error:", err.message);
          setDestinationRoadNode(null);
          setDestinationNodeError(err.message);
          setDestinationNodeLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [destinationLocation]);

  return (
    <NavigationContext.Provider
      value={{
        mapInstance,
        setMapInstance,
        center,
        setCenter,
        zoom,
        setZoom,
        userLocation,
        setUserLocation,
        currentLocation,
        setCurrentLocation,
        sourceText,
        setSourceText,
        destinationText,
        setDestinationText,
        sourceLocation,
        setSourceLocation,
        destinationLocation,
        setDestinationLocation,
        sourceRoadNode,
        setSourceRoadNode,
        destinationRoadNode,
        setDestinationRoadNode,
        sourceNodeLoading,
        destinationNodeLoading,
        sourceNodeError,
        destinationNodeError,
        isDebugMode,
        setIsDebugMode,
        activeRoute,
        setActiveRoute,
        routeLoading,
        routeError,
        selectedAlgorithm,
        setSelectedAlgorithm,
        selectedRoutingMode,
        setSelectedRoutingMode,
        
        // Sprint 10, 11 & 11C & Alternative Route Engine
        comparisonData,
        rerouteRecommendation,
        isAlternativeCalculating,
        handleGenerateAlternativeRoutes,
        previewRoute,
        setPreviewRoute,
        isRouteSwitching,
        routeSwitchError,
        clearRouteSwitchError: () => setRouteSwitchError(null),
        acceptReroute: async (customRoute) => {
          if (isRouteSwitching) return;
          const targetRoute = customRoute || previewRoute || (rerouteRecommendation && rerouteRecommendation.alternative_route);
          if (!targetRoute) return;

          setIsRouteSwitching(true);
          setRouteSwitchError(null);
          try {
            await backendSetActiveRoute(targetRoute, targetRoute.algorithm || selectedAlgorithm, targetRoute.routing_mode || selectedRoutingMode, "User accepted alternative route with lower traffic cost");
            setActiveRoute(targetRoute);
            if (targetRoute.algorithm) setSelectedAlgorithm(targetRoute.algorithm);
            setRerouteRecommendation(prev => prev ? { ...prev, status: "COOLDOWN", alternative_routes: [], alternative_route: null } : null);
            setPreviewRoute(null);
          } catch(e) { 
            console.error("Failed to accept reroute:", e); 
            setRouteSwitchError("Unable to switch route. Your current route remains active.");
          } finally {
            setIsRouteSwitching(false);
          }
        },
        rejectReroute: async () => {
          try {
            await backendRejectReroute();
            setRerouteRecommendation(prev => prev ? { ...prev, status: "COOLDOWN", alternative_routes: [], alternative_route: null } : null);
            setPreviewRoute(null);
          } catch(e) { console.error("Failed to reject reroute:", e); }
        },

        calculateAndSetRoute,
        handleClearRoute,
        visibleLayers,
        setVisibleLayers,
        visibleOverlays,
        setVisibleOverlays,
        trafficMode,
        setTrafficMode,
        // ── Sprint 4.4: Vehicle Simulation ──
        vehicles,
        setVehicles,
        simulationStatus,
        simulationError,
        lastUpdateTime,
        handleGenerateVehicles,
        handleStartSimulation,
        handlePauseSimulation,
        handleResumeSimulation,
        handleResetSimulation,
        // ── Sprint 6.5 & 6.6B: Traffic Hotspots ──
        hotspotsData,
        hotspotsError,
        isTrafficUpdating,
        trafficLastUpdated,
        // ── Sprint 8: Clustering ──
        clustersData,
        setClustersData,
        // ── On-Demand Alternative Routes (AlternativeRoutesCard) ──
        alternativeRoutes,
        isGeneratingAlternatives,
        alternativeGenerationError,
        simulationStartedAt,
        alternativeAnalysisStatus,
        handleGenerateAlternatives,
      }}
    >
      {children}
    </NavigationContext.Provider>
  );
};

export const NavigationEngineProvider = NavigationProvider;

export const useNavigationEngineContext = () => {
  const ctx = useContext(NavigationContext);
  if (!ctx) {
    throw new Error("useNavigationEngineContext must be used within NavigationProvider");
  }
  return ctx;
};
