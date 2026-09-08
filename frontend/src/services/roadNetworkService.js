/**
 * roadNetworkService.js — Resilient Road Network & Routing API Service
 *
 * Utilizes the central apiClient with:
 *   - Service-specific timeout budgets (Routing: 20s, Nearest Node: 8s, Alternatives: 15s)
 *   - Automatic correlation ID (X-Request-ID)
 *   - Bounded retry for transient errors
 *   - Safe cancellation handling
 */
import { apiClient, TIMEOUT_BUDGETS } from "./api";

/**
 * findNearestRoadNode
 * Calls GET /api/road-network/nodes/nearest?lat=<LAT>&lon=<LON>
 */
export const findNearestRoadNode = async (latitude, longitude, signal = null) => {
  const lat = Number(latitude);
  const lon = Number(longitude);

  if (!isFinite(lat) || !isFinite(lon)) {
    throw new Error("Invalid coordinates provided for road network lookup.");
  }

  try {
    const response = await apiClient.get("/api/road-network/nodes/nearest", {
      params: { lat, lon },
      timeout: TIMEOUT_BUDGETS.GEOCODING,
      signal: signal || undefined,
    });

    if (response.data && response.data.status === "success" && response.data.nearest_node) {
      const node = response.data.nearest_node;
      return {
        nodeId: String(node.node_id),
        latitude: Number(node.latitude),
        longitude: Number(node.longitude),
        distance: Number(node.distance_km),
      };
    }

    throw new Error(response.data?.message || "Nearest road node unavailable.");
  } catch (error) {
    if (error.name === "AbortError" || error.isCancelled) {
      throw error;
    }
    const reason = error.data?.reason || error.response?.data?.reason;
    if (reason === "OUTSIDE_NETWORK_COVERAGE" || error.data?.error === "LOCATION_OUTSIDE_ROAD_NETWORK") {
      throw new Error("Location is outside the available road network.");
    }
    throw new Error(error.message || "Road network service is temporarily unavailable.");
  }
};

export const roadNetworkService = {
  findNearestRoadNode,
  getSummary: async () => {
    const response = await apiClient.get("/api/road-network/summary", {
      timeout: TIMEOUT_BUDGETS.DEFAULT,
    });
    return response.data;
  },
};

/**
 * calculateRoute
 * Calls POST /api/routes/calculate
 */
export const calculateRoute = async (
  sourceNodeId,
  destinationNodeId,
  srcCoords = null,
  dstCoords = null,
  algorithm = "astar",
  routingMode = "normal",
  sourceName = null,
  destinationName = null,
  signal = null,
  requestId = null
) => {
  if (!sourceNodeId || !destinationNodeId) {
    throw new Error("Both source and destination node IDs are required.");
  }

  const body = {
    source_node:      String(sourceNodeId),
    destination_node: String(destinationNodeId),
    algorithm:        algorithm || "astar",
    routing_mode:     routingMode || "normal",
  };
  if (sourceName) body.source_name = sourceName;
  if (destinationName) body.destination_name = destinationName;
  if (srcCoords && isFinite(srcCoords.lat) && isFinite(srcCoords.lon)) {
    body.source_lat = srcCoords.lat;
    body.source_lon = srcCoords.lon;
  }
  if (dstCoords && isFinite(dstCoords.lat) && isFinite(dstCoords.lon)) {
    body.destination_lat = dstCoords.lat;
    body.destination_lon = dstCoords.lon;
  }
  if (requestId) {
    body.request_id = requestId;
  }

  try {
    const response = await apiClient.post("/api/routes/calculate", body, {
      timeout: TIMEOUT_BUDGETS.ROUTING,
      signal: signal || undefined,
      requestId: requestId || undefined,
      idempotencyKey: requestId || undefined,
      operationKey: "route_calculation",
    });

    if (response.data && response.data.success && response.data.route) {
      return response.data.route;
    }
    throw new Error(response.data?.error || response.data?.message || "Route calculation failed.");
  } catch (error) {
    if (error.name === "AbortError" || error.isCancelled) {
      throw error;
    }
    if (error.code === "TIMEOUT" || error.data?.error === "ROUTE_TIMEOUT") {
      throw new Error("Route calculation exceeded timeout budget. Please select closer points.");
    }
    throw new Error(error.message || "Route calculation failed.");
  }
};

/**
 * compareAlgorithms
 * Runs backend comparison benchmark between A* and Dijkstra.
 */
export const compareAlgorithms = async (
  sourceNodeId,
  destinationNodeId,
  srcCoords = null,
  dstCoords = null,
  routingMode = "normal",
  signal = null
) => {
  const body = {
    source_node:      String(sourceNodeId),
    destination_node: String(destinationNodeId),
    routing_mode:     routingMode || "normal",
  };
  if (srcCoords && isFinite(srcCoords.lat) && isFinite(srcCoords.lon)) {
    body.source_lat = srcCoords.lat;
    body.source_lon = srcCoords.lon;
  }
  if (dstCoords && isFinite(dstCoords.lat) && isFinite(dstCoords.lon)) {
    body.destination_lat = dstCoords.lat;
    body.destination_lon = dstCoords.lon;
  }

  const response = await apiClient.post("/api/routes/compare", body, {
    timeout: TIMEOUT_BUDGETS.ROUTING,
    signal: signal || undefined,
  });
  return response.data;
};

/**
 * setActiveRoute
 * Explicitly sets the active route on the backend.
 */
export const setActiveRoute = async (
  route,
  algorithm = "astar",
  routingMode = "traffic_aware",
  reason = "User updated route"
) => {
  const response = await apiClient.post("/api/routes/active", {
    route,
    algorithm,
    routing_mode: routingMode,
    reason,
  });
  return response.data;
};

/**
 * rejectReroute
 * Rejects a reroute recommendation and resets the cooldown timer.
 */
export const rejectReroute = async () => {
  const response = await apiClient.post("/api/routes/active/reject");
  return response.data;
};

/**
 * fetchAlternativeRoutes
 * Calls POST /api/routes/alternatives.
 */
export const fetchAlternativeRoutes = async (
  sourceNodeId,
  destinationNodeId,
  currentRoute = null,
  trafficLevel = "HIGH",
  maxAlternatives = 2,
  requestId = null,
  routingMode = "traffic_aware",
  algorithm = "astar",
  signal = null
) => {
  if (!sourceNodeId || !destinationNodeId) {
    throw new Error("Source and destination node IDs are required.");
  }

  const payload = {
    source:           String(sourceNodeId),
    destination:      String(destinationNodeId),
    current_route:    currentRoute || null,
    traffic_level:    trafficLevel,
    routing_mode:     routingMode,
    algorithm:        algorithm,
    max_alternatives: Math.max(1, Math.min(2, maxAlternatives)),
    request_id:       requestId,
  };

  try {
    const response = await apiClient.post("/api/routes/alternatives", payload, {
      timeout: TIMEOUT_BUDGETS.ALTERNATIVES,
      signal: signal || undefined,
      requestId: requestId || undefined,
      operationKey: "alternative_routes",
    });
    return response.data;
  } catch (error) {
    if (error.name === "AbortError" || error.isCancelled) {
      throw new DOMException("Request was cancelled.", "AbortError");
    }
    if (error.code === "TIMEOUT") {
      return {
        success: false,
        status: "error",
        count: 0,
        alternatives: [],
        error: { code: "NETWORK_TIMEOUT", message: "Alternative route request timed out." },
      };
    }
    if (error.data) {
      return error.data;
    }
    return {
      success: false,
      status: "error",
      count: 0,
      alternatives: [],
      error: { code: error.code || "NETWORK_ERROR", message: error.message || "Network error." },
    };
  }
};
