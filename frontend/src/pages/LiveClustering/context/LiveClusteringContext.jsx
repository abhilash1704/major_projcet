/**
 * LiveClusteringContext — Live Vehicle Clustering Context with Automatic 20s Cycle & Countdown
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  analyzeArea as apiAnalyzeArea,
  fetchSnapshot as apiFetchSnapshot,
  fetchRealTraffic as apiFetchRealTraffic,
} from "../services/liveClusteringApi";
import { MONITORING_AREAS } from "../services/monitoringAreas";

const DEFAULT_AREA = MONITORING_AREAS[0] || {
  id: "silk_board",
  name: "Silk Board Junction",
  latitude: 12.9174,
  longitude: 77.6228,
  source: "preset",
};

const CYCLE_INTERVAL_SECONDS = 20;

const LiveClusteringContext = createContext(null);

export const LiveClusteringProvider = ({ children }) => {
  const [selectedArea, setSelectedArea]                 = useState(DEFAULT_AREA);
  const [analysisRadiusMeters, setAnalysisRadiusMeters] = useState(1000);
  const [countdownSeconds, setCountdownSeconds]         = useState(CYCLE_INTERVAL_SECONDS);
  const [sessionId, setSessionId]                       = useState(null);
  
  // Simulation GPS & Replay State
  const [simulationGps, setSimulationGps]               = useState({
    status: "LIVE",
    source: "SIMULATION_STORE",
    vehicles_in_area: 0,
    user_observations: 0,
    observation_window_seconds: 5.0,
  });
  const [observations, setObservations]                 = useState([]);
  
  // Clustering, Mapping, Evaluation & Traffic State
  const [clustering, setClustering]                     = useState({ status: "INACTIVE", clusters: [], metrics: {} });
  const [roadDensity, setRoadDensity]                   = useState({ status: "INACTIVE", road_segments: [], total_active_edges: 0 });
  const [evaluation, setEvaluation]                     = useState({ status: "INACTIVE" });
  const [realTraffic, setRealTraffic]                   = useState(null);

  // Selection & Filter State
  const [selectedCluster, setSelectedCluster]           = useState(null);
  const [selectedSegment, setSelectedSegment]           = useState(null);
  const [selectedDensityFilter, setSelectedDensityFilter] = useState(null); // null | 'HIGH' | 'MEDIUM' | 'LOW'
  
  const [status, setStatus]                             = useState("IDLE");
  const [error, setError]                               = useState(null);

  const selectedAreaRef  = useRef(selectedArea);
  const radiusRef        = useRef(analysisRadiusMeters);
  const isPollingRef     = useRef(false);
  const activeCycleSeqRef = useRef(0);
  const pollAbortRef     = useRef(null);

  useEffect(() => {
    selectedAreaRef.current = selectedArea;
    radiusRef.current = analysisRadiusMeters;
  }, [selectedArea, analysisRadiusMeters]);

  // ── Toggle Density Filter (HIGH / MEDIUM / LOW) ──────────────────────────
  const toggleDensityFilter = useCallback((level) => {
    setSelectedDensityFilter((prev) => (prev === level ? null : level));
  }, []);

  const clearDensityFilter = useCallback(() => {
    setSelectedDensityFilter(null);
  }, []);

  // ── Fetch Full Snapshot (Resilient, preserves snapshot on failure) ────────
  const pollSnapshot = useCallback(async () => {
    if (isPollingRef.current) return;
    isPollingRef.current = true;

    // Abort previous in-flight poll if any
    if (pollAbortRef.current) {
      pollAbortRef.current.abort();
    }
    const controller = new AbortController();
    pollAbortRef.current = controller;
    const currentSeq = activeCycleSeqRef.current;

    try {
      const snapRes = await apiFetchSnapshot(controller.signal);
      if (currentSeq !== activeCycleSeqRef.current) return; // Stale cycle discarded

      if (snapRes?.snapshot) {
        const s = snapRes.snapshot;
        if (s.session_id) setSessionId(s.session_id);
        if (s.simulation) setSimulationGps(s.simulation);
        if (s.clustering) setClustering(s.clustering);
        if (s.road_density) setRoadDensity(s.road_density);
        if (s.evaluation) setEvaluation(s.evaluation);
        if (s.window_observations) setObservations(s.window_observations);
        setStatus(s.status || "LIVE");
        setError(null);
      }

      // Fetch separate real traffic panel data
      try {
        const trafficRes = await apiFetchRealTraffic(selectedAreaRef.current, radiusRef.current, controller.signal);
        if (currentSeq === activeCycleSeqRef.current && trafficRes?.traffic) {
          setRealTraffic(trafficRes.traffic);
        }
      } catch (trafficErr) {
        // External traffic failure degrades gracefully; never crashes clustering
        console.warn("[LiveClusteringContext] Traffic provider unavailable, continuing with clustering:", trafficErr.message);
      }
    } catch (err) {
      if (err.name === "AbortError" || err.isCancelled) return;
      if (currentSeq !== activeCycleSeqRef.current) return;
      console.warn("[LiveClusteringContext] Cycle update failed — preserving previous valid snapshot:", err.message);
      // Requirement 18: Keep previous valid snapshot. Retry next scheduled cycle.
    } finally {
      isPollingRef.current = false;
    }
  }, []);

  // ── Analyze Area (Cancels previous cycle & starts new one) ───────────────
  const analyzeArea = useCallback(async (area, radiusMeters = 1000) => {
    const newSeq = ++activeCycleSeqRef.current;
    if (pollAbortRef.current) {
      pollAbortRef.current.abort();
      pollAbortRef.current = null;
    }

    setSelectedArea({ ...area });
    setAnalysisRadiusMeters(radiusMeters);
    setStatus("STARTING_LIVE_ANALYSIS");
    setError(null);
    setSelectedCluster(null);
    setSelectedSegment(null);
    setSelectedDensityFilter(null);

    // Clear old area markers & clusters immediately
    setObservations([]);
    setClustering({ status: "INACTIVE", clusters: [], metrics: {} });
    setRoadDensity({ status: "INACTIVE", road_segments: [], total_active_edges: 0 });
    setEvaluation({ status: "INACTIVE" });
    setCountdownSeconds(CYCLE_INTERVAL_SECONDS);

    const controller = new AbortController();
    pollAbortRef.current = controller;

    try {
      const res = await apiAnalyzeArea(area, radiusMeters, controller.signal);
      if (newSeq !== activeCycleSeqRef.current) return; // Stale request discarded

      if (res?.snapshot) {
        const s = res.snapshot;
        if (s.session_id) setSessionId(s.session_id);
        if (s.simulation) setSimulationGps(s.simulation);
        if (s.clustering) setClustering(s.clustering);
        if (s.road_density) setRoadDensity(s.road_density);
        if (s.evaluation) setEvaluation(s.evaluation);
        if (s.window_observations) setObservations(s.window_observations);
      }
      setStatus("LIVE");
    } catch (err) {
      if (err.name === "AbortError" || err.isCancelled) return;
      if (newSeq !== activeCycleSeqRef.current) return;
      setStatus("ERROR");
      setError(err.message || "Failed to analyze area");
    }
  }, []);

  // ── 1-Second Countdown Ticker & Single Controlled 20-Second Refresh Loop ─
  useEffect(() => {
    pollSnapshot();

    const interval = setInterval(() => {
      setCountdownSeconds((prev) => {
        if (prev <= 1) {
          pollSnapshot();
          return CYCLE_INTERVAL_SECONDS;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      clearInterval(interval);
      if (pollAbortRef.current) {
        pollAbortRef.current.abort();
      }
    };
  }, [pollSnapshot]);

  const value = {
    selectedArea,
    analysisRadiusMeters,
    setAnalysisRadiusMeters,
    analyzeArea,
    countdownSeconds,
    sessionId,
    
    // Simulation GPS & Observations
    simulationGps,
    observations,
    
    // Clustering, Density, Evaluation & Traffic
    clustering,
    roadDensity,
    evaluation,
    realTraffic,

    // Selection & Filter State
    selectedCluster,
    setSelectedCluster,
    selectedSegment,
    setSelectedSegment,
    selectedDensityFilter,
    setSelectedDensityFilter,
    toggleDensityFilter,
    clearDensityFilter,

    status,
    error,
  };

  return (
    <LiveClusteringContext.Provider value={value}>
      {children}
    </LiveClusteringContext.Provider>
  );
};

export const useLiveClustering = () => {
  const ctx = useContext(LiveClusteringContext);
  if (!ctx) {
    throw new Error("useLiveClustering must be used within LiveClusteringProvider");
  }
  return ctx;
};
