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
  const alternativeRequestIdRef = useRef(0);
  const alternativeRouteRequestIdRef = alternativeRequestIdRef;
  const analysisTimerRef = useRef(null);  // 5-second delay timer
  const altAbortControllerRef = useRef(null);
  const routeSequenceRef = useRef(0);
  const routeAbortControllerRef = useRef(null);


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

    // Cancel any in-flight request
    if (altAbortControllerRef.current) altAbortControllerRef.current.abort();
    const abortCtrl = new AbortController();
    altAbortControllerRef.current = abortCtrl;

    const reqId = ++alternativeRequestIdRef.current;
    setIsAlternativeCalculating(true);

    const currDist = activeRoute.total_distance_km || activeRoute.distance_km || 0;
    const currEta  = Math.round((activeRoute.total_travel_time_seconds || 0) / 60);

    setRerouteRecommendation({
      status: "CALCULATING",
      reason: "Finding best alternatives...",
      current_route: {
        distance_km:   currDist,
        eta_minutes:   currEta,
        traffic_level: "HIGH",
        traffic_cost:  activeRoute.traffic_cost || 0,
      },
      alternatives: [],
    });

    try {
      const data = await fetchAlternativeRoutes(
        srcId, dstId, activeRoute, "HIGH", 2, reqId,
        selectedRoutingMode, selectedAlgorithm, abortCtrl.signal
      );

      if (alternativeRequestIdRef.current !== reqId) return; // stale

      setIsAlternativeCalculating(false);

      if (data?.success) {
        const alts = data.alternatives || [];
        if (alts.length > 0) {
          setRerouteRecommendation({
            status: "REROUTE_AVAILABLE",
            reason: `Found ${alts.length} alternative route(s).`,
            current_route: data.current_route || { distance_km: currDist, eta_minutes: currEta, traffic_level: "HIGH" },
            alternative_routes: alts,
            alternatives: alts,
            generation_time_ms: data.generation_time_ms || data.execution_time_ms,
          });
        } else {
          setRerouteRecommendation({
            status: "NO_BETTER_ROUTE",
            reason: data.message || "No suitable alternative route found.",
            current_route: data.current_route || { distance_km: currDist, eta_minutes: currEta, traffic_level: "HIGH" },
            alternative_routes: [],
            alternatives: [],
          });
        }
      } else if (data?.error?.code === "ROUTE_GENERATION_TIMEOUT") {
        setRerouteRecommendation({
          status: "TIMEOUT",
          reason: "Route generation timed out.",
          current_route: { distance_km: currDist, eta_minutes: currEta, traffic_level: "HIGH" },
          alternative_routes: [],
          alternatives: [],
        });
      } else {
        setRerouteRecommendation({
          status: "ERROR",
          reason: data?.error?.message || data?.message || "Failed to calculate alternative routes.",
          current_route: { distance_km: currDist, eta_minutes: currEta, traffic_level: "HIGH" },
          alternative_routes: [],
          alternatives: [],
        });
      }
    } catch (err) {
      if (err.name === "AbortError") return; // intentional cancellation — no state update
      if (alternativeRequestIdRef.current === reqId) {
        setIsAlternativeCalculating(false);
        setRerouteRecommendation({
          status: "ERROR",
          reason: err.message || "Failed to generate alternative routes.",
          current_route: { distance_km: currDist, eta_minutes: currEta, traffic_level: "HIGH" },
          alternative_routes: [],
          alternatives: [],
        });
      }
    }
  }, [activeRoute, isAlternativeCalculating, selectedRoutingMode, selectedAlgorithm]);

  // ── On-Demand Alternative Route Generation (AlternativeRoutesCard) ───────
  const handleGenerateAlternatives = useCallback(async () => {
    // Idempotency guard: ignore if already generating
    if (!activeRoute || isGeneratingAlternatives) return;

    const srcId = activeRoute.source_node_id || activeRoute.source_node;
    const dstId = activeRoute.target_node_id || activeRoute.destination_node;
    if (!srcId || !dstId) return;

    // Clear any pending auto-trigger timer — manual click supersedes it
    if (analysisTimerRef.current) {
      clearTimeout(analysisTimerRef.current);
      analysisTimerRef.current = null;
    }

    // Cancel any in-flight request
    if (altAbortControllerRef.current) altAbortControllerRef.current.abort();
    const abortCtrl = new AbortController();
    altAbortControllerRef.current = abortCtrl;

    const reqId = ++alternativeRequestIdRef.current;
    setIsGeneratingAlternatives(true);
    setAlternativeGenerationError(null);
    setAlternativeRoutes([]);
    setAlternativeAnalysisStatus("analyzing");

    // Safety timeout: 25 s hard frontend ceiling
    let timeoutId = null;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => {
        abortCtrl.abort();
        reject(new Error("FRONTEND_TIMEOUT"));
      }, 25000);
    });

    try {
      const data = await Promise.race([
        fetchAlternativeRoutes(
          srcId, dstId, activeRoute, "HIGH", 2, reqId,
          selectedRoutingMode, selectedAlgorithm, abortCtrl.signal
        ),
        timeoutPromise,
      ]);
      clearTimeout(timeoutId);

      // Stale request protection
      if (alternativeRequestIdRef.current !== reqId) return;

      // ── Validate response structure ──────────────────────────────────────
      if (!data || typeof data !== "object") {
        setAlternativeGenerationError("Received an unexpected response from the server.");
        setAlternativeAnalysisStatus("error");
        return;
      }

      if (data.success) {
        const alts = Array.isArray(data.alternatives) ? data.alternatives : [];
        // Validate each alternative before rendering
        const validAlts = alts.filter(
          (a) =>
            a &&
            typeof (a.distance_km ?? a.total_distance_km) === "number" &&
            isFinite(a.distance_km ?? a.total_distance_km) &&
            (a.distance_km ?? a.total_distance_km) > 0 &&
            Array.isArray(a.nodes || a.path)
        );
        setAlternativeRoutes(validAlts);
        if (validAlts.length === 0) {
          // zero alternatives is a valid outcome — not an error
          setAlternativeGenerationError(null);
          setAlternativeAnalysisStatus("no_alternatives");
        } else {
          setAlternativeAnalysisStatus("done");
        }
      } else {
        // Structured error from backend
        const errMsg =
          data?.error?.message ||
          data?.message ||
          (data?.error?.code === "ROUTE_GENERATION_TIMEOUT"
            ? "Alternative route analysis timed out. Please try again."
            : "Failed to generate alternative routes.");
        setAlternativeGenerationError(errMsg);
        setAlternativeAnalysisStatus("error");
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === "AbortError") {
        if (alternativeRequestIdRef.current === reqId) {
          setAlternativeAnalysisStatus("cancelled");
        }
        return;
      }
      if (alternativeRequestIdRef.current !== reqId) return;
      if (err.message === "FRONTEND_TIMEOUT") {
        setAlternativeGenerationError(
          "Alternative route analysis timed out. Current route is still active."
        );
      } else {
        setAlternativeGenerationError(
          err.message || "Failed to generate alternative routes."
        );
      }
      setAlternativeAnalysisStatus("error");
    } finally {
      if (alternativeRequestIdRef.current === reqId) {
        setIsGeneratingAlternatives(false);
      }
    }
  }, [activeRoute, isGeneratingAlternatives, selectedRoutingMode, selectedAlgorithm]);

  // ── Select and Switch to an Alternative Route (Prompt Section 24) ─────────
  const handleSelectAlternativeRoute = useCallback(async (altRoute) => {
    if (!altRoute || isRouteSwitching) return false;
    const nodes = altRoute.nodes || altRoute.path;
    if (!Array.isArray(nodes) || nodes.length < 2) {
      setRouteSwitchError("Selected alternative route has invalid nodes.");
      return false;
    }
    const dist = altRoute.distance_km || altRoute.total_distance_km;
    if (typeof dist !== "number" || dist <= 0 || !isFinite(dist)) {
      setRouteSwitchError("Selected alternative route has invalid distance.");
      return false;
    }

    setIsRouteSwitching(true);
    setRouteSwitchError(null);

    try {
      const targetRoute = {
        ...altRoute,
        source_node_id: altRoute.source_node || (typeof nodes[0] === "object" ? nodes[0].id : nodes[0]),
        target_node_id: altRoute.destination_node || (typeof nodes[nodes.length - 1] === "object" ? nodes[nodes.length - 1].id : nodes[nodes.length - 1]),
        total_distance_km: dist,
        distance_km: dist,
        total_travel_time_seconds: altRoute.travel_time_seconds || (altRoute.eta_minutes * 60),
        travel_time_seconds: altRoute.travel_time_seconds || (altRoute.eta_minutes * 60),
        status: "success",
        success: true,
      };

      try {
        await backendSetActiveRoute(
          targetRoute,
          altRoute.algorithm === "Dijkstra" ? "dijkstra" : "astar",
          selectedRoutingMode,
          "User selected alternative route"
        );
      } catch (beErr) {
        console.warn("Backend active route sync notice:", beErr.message);
      }

      setActiveRoute(targetRoute);
      setAlternativeRoutes((prev) =>
        prev.filter((r) => (r.route_id || r.id) !== (altRoute.route_id || altRoute.id))
      );
      return true;
    } catch (err) {
      console.error("Failed to select alternative route:", err);
      setRouteSwitchError("Unable to switch to alternative route. Current route remains active.");
      return false;
    } finally {
      setIsRouteSwitching(false);
    }
  }, [isRouteSwitching, selectedRoutingMode, setActiveRoute]);

  // ── Auto-trigger alternative analysis 5s after simulation starts ─────────
  useEffect(() => {
    if (analysisTimerRef.current) {
      clearTimeout(analysisTimerRef.current);
      analysisTimerRef.current = null;
    }

    if (
      simulationStatus !== "running" ||
      !activeRoute ||
      isGeneratingAlternatives ||
      (alternativeRoutes && alternativeRoutes.length > 0) ||
      alternativeAnalysisStatus === "analyzing" ||
      alternativeAnalysisStatus === "done" ||
      alternativeAnalysisStatus === "no_alternatives"
    ) {
      return;
    }

    setSimulationStartedAt(Date.now());
    setAlternativeAnalysisStatus("waiting");

    // 5-second delayed auto-analysis
    analysisTimerRef.current = setTimeout(() => {
      analysisTimerRef.current = null;
      // Guard: only run if still in waiting state (manual click may have started it)
      setAlternativeAnalysisStatus((prev) => {
        if (prev === "waiting") {
          handleGenerateAlternatives();
        }
        return prev;
      });
    }, 5000);

    return () => {
      if (analysisTimerRef.current) {
        clearTimeout(analysisTimerRef.current);
        analysisTimerRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [simulationStatus, activeRoute]);

  // ── Abort in-flight requests on unmount ───────────────────────────────────
  useEffect(() => {
    return () => {
      if (altAbortControllerRef.current) {
        altAbortControllerRef.current.abort();
      }
      if (routeAbortControllerRef.current) {
        routeAbortControllerRef.current.abort();
      }
    };
  }, []);


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

    // Cancel prior in-flight route calculation (Requirement 4 & 14)
    if (routeAbortControllerRef.current) {
      routeAbortControllerRef.current.abort();
    }
    const controller = new AbortController();
    routeAbortControllerRef.current = controller;
    const currentSeq = ++routeSequenceRef.current;

    setRouteLoading(true);
    setRouteError(null);

    try {
      const route = await calculateRoute(
        srcNodeId, dstNodeId, srcCoords, dstCoords, algorithm, routingMode, srcName, dstName,
        controller.signal, `route_${currentSeq}`
      );

      // Discard stale out-of-order response (Requirement 14 & 19)
      if (currentSeq !== routeSequenceRef.current) {
        console.info(`[NavigationEngine] Discarded stale route calculation response #${currentSeq} (latest is #${routeSequenceRef.current})`);
        return null;
      }

      if (route) {
        // Step 9 — Only replace existing route after both endpoints resolve and new route is calculated
        setActiveRoute(route);

        // Invalidate stale alternative calculations & cancel any in-flight request
        if (altAbortControllerRef.current) altAbortControllerRef.current.abort();
        alternativeRequestIdRef.current++;
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
        compareAlgorithms(srcNodeId, dstNodeId, srcCoords, dstCoords, routingMode, controller.signal)
          .then((data) => {
            if (currentSeq === routeSequenceRef.current) setComparisonData(data);
          })
          .catch((err) => {
            if (err.name !== "AbortError") {
              console.warn("Background algorithm comparison notice:", err.message);
            }
          });
      }
      return route;
    } catch (err) {
      if (err.name === "AbortError" || err.isCancelled) {
        return null;
      }
      if (currentSeq !== routeSequenceRef.current) {
        return null;
      }
      console.error("Route calculation failed:", err.message);
      setRouteError(err.message || "Unable to calculate route. Current page remains usable.");
      return null;
    } finally {
      if (currentSeq === routeSequenceRef.current) {
        setRouteLoading(false);
      }
    }
  }, []);

  // ── Route Clear — STATE 7 ───────────────────────────────────────────────
  const handleClearRoute = useCallback(async () => {
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current);
      simulationIntervalRef.current = null;
    }
    // Invalidate stale alternative calculations & cancel any in-flight request
    if (altAbortControllerRef.current) altAbortControllerRef.current.abort();
    alternativeRequestIdRef.current++;
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
        handleSelectAlternativeRoute,
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
