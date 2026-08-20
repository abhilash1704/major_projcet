import axios from 'axios';

// Base API URL for backend endpoints
const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:5000';

/**
 * findNearestRoadNode — Sprint 5.4
 *
 * Calls GET /api/road-network/nodes/nearest?lat=<LAT>&lon=<LON>
 * to find the nearest Road Network Node to given geographic coordinates.
 *
 * @param {number|string} latitude
 * @param {number|string} longitude
 * @returns {Promise<{nodeId: string, latitude: number, longitude: number, distance: number}>}
 */
export const findNearestRoadNode = async (latitude, longitude) => {
  const lat = Number(latitude);
  const lon = Number(longitude);

  if (!isFinite(lat) || !isFinite(lon)) {
    throw new Error("Invalid coordinates provided for road network lookup.");
  }

  try {
    const response = await axios.get(`${BACKEND_BASE_URL}/api/road-network/nodes/nearest`, {
      params: { lat, lon },
      timeout: 60000
    });

    if (response.data && response.data.status === 'success' && response.data.nearest_node) {
      const node = response.data.nearest_node;
      return {
        nodeId: String(node.node_id),
        latitude: Number(node.latitude),
        longitude: Number(node.longitude),
        distance: Number(node.distance_km)
      };
    }

    throw new Error(response.data?.message || "Nearest road node unavailable.");
  } catch (error) {
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      throw new Error("Road network service is temporarily unavailable.");
    } else if (error.response) {
      const reason = error.response.data?.reason;
      if (reason === 'OUTSIDE_NETWORK_COVERAGE' || error.response.data?.error === 'LOCATION_OUTSIDE_ROAD_NETWORK') {
        throw new Error("Location is outside the available road network.");
      }
      throw new Error(error.response.data?.message || "Road network service is temporarily unavailable.");
    } else if (error.request) {
      throw new Error("Road network service is temporarily unavailable.");
    } else {
      throw new Error(error.message || "Road network service is temporarily unavailable.");
    }
  }
};

export const roadNetworkService = {
  findNearestRoadNode,
  getSummary: async () => {
    const response = await axios.get(`${BACKEND_BASE_URL}/api/road-network/summary`);
    return response.data;
  }
};

/**
 * calculateRoute — Sprint 5.3 / 5.5
 *
 * Calls POST /api/routes/calculate with source and destination road node IDs,
 * chosen algorithm ('astar' | 'dijkstra'), and optionally raw coordinates.
 *
 * @param {string} sourceNodeId
 * @param {string} destinationNodeId
 * @param {{ lat: number, lon: number }|null} srcCoords
 * @param {{ lat: number, lon: number }|null} dstCoords
 * @param {string} algorithm ('astar' | 'dijkstra')
 * @returns {Promise<{nodes, edges, total_distance_km, total_travel_time_seconds, algorithm}>}
 */
export const calculateRoute = async (
  sourceNodeId,
  destinationNodeId,
  srcCoords = null,
  dstCoords = null,
  algorithm = 'astar',
  routingMode = 'normal',
  sourceName = null,
  destinationName = null
) => {
  if (!sourceNodeId || !destinationNodeId) {
    throw new Error('Both source and destination node IDs are required.');
  }
  const body = {
    source_node:      String(sourceNodeId),
    destination_node: String(destinationNodeId),
    algorithm:        algorithm || 'astar',
    routing_mode:     routingMode || 'normal',
  };
  if (sourceName) body.source_name = sourceName;
  if (destinationName) body.destination_name = destinationName;
  // Forward coordinates so the backend can call ensure_graph_for_points()
  if (srcCoords && isFinite(srcCoords.lat) && isFinite(srcCoords.lon)) {
    body.source_lat = srcCoords.lat;
    body.source_lon = srcCoords.lon;
  }
  if (dstCoords && isFinite(dstCoords.lat) && isFinite(dstCoords.lon)) {
    body.destination_lat = dstCoords.lat;
    body.destination_lon = dstCoords.lon;
  }
  try {
    const response = await axios.post(
      `${BACKEND_BASE_URL}/api/routes/calculate`,
      body,
      { timeout: 60000 }
    );
    if (response.data && response.data.success && response.data.route) {
      return response.data.route;
    }
    throw new Error(response.data?.error || 'Route calculation failed.');
  } catch (error) {
    if (error.response?.data?.error === 'ROUTE_TIMEOUT') {
      throw new Error("Route calculation exceeded 40 seconds. Please try a closer source and destination.");
    }
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      throw new Error("Route calculation timed out. Please try again.");
    } else if (error.response) {
      throw new Error(error.response.data?.error || `Route API error (${error.response.status})`);
    } else if (error.request) {
      throw new Error('Route calculation service is unreachable. Please check server.');
    }
    throw error;
  }
};

/**
 * compareAlgorithms — Sprint 5.3
 * Runs backend comparison benchmark between A* and Dijkstra.
 */
export const compareAlgorithms = async (
  sourceNodeId,
  destinationNodeId,
  srcCoords = null,
  dstCoords = null,
  routingMode = 'normal'
) => {
  const body = {
    source_node:      String(sourceNodeId),
    destination_node: String(destinationNodeId),
    routing_mode:     routingMode || 'normal',
  };
  if (srcCoords && isFinite(srcCoords.lat) && isFinite(srcCoords.lon)) {
    body.source_lat = srcCoords.lat;
    body.source_lon = srcCoords.lon;
  }
  if (dstCoords && isFinite(dstCoords.lat) && isFinite(dstCoords.lon)) {
    body.destination_lat = dstCoords.lat;
    body.destination_lon = dstCoords.lon;
  }
  const response = await axios.post(
    `${BACKEND_BASE_URL}/api/routes/compare`,
    body,
    { timeout: 60000 }
  );
  return response.data;
};

/**
 * setActiveRoute — Sprint 11
 * Explicitly sets the active route on the backend.
 */
export const setActiveRoute = async (route, algorithm = 'astar', routingMode = 'traffic_aware', reason = 'User updated route') => {
  const response = await axios.post(
    `${BACKEND_BASE_URL}/api/routes/active`,
    {
      route,
      algorithm,
      routing_mode: routingMode,
      reason
    }
  );
  return response.data;
};

/**
 * rejectReroute — Sprint 11
 * Rejects a reroute recommendation and resets the cooldown timer.
 */
export const rejectReroute = async () => {
  const response = await axios.post(
    `${BACKEND_BASE_URL}/api/routes/active/reject`
  );
  return response.data;
};

/**
 * fetchAlternativeRoutes — High-Traffic Alternative Route Engine
 * Calls POST /api/routes/alternatives when HIGH traffic occurs.
 */
export const fetchAlternativeRoutes = async (sourceNodeId, destinationNodeId, currentRoute, trafficLevel = "HIGH", maxAlternatives = 3, requestId = null) => {
  const response = await axios.post(
    `${BACKEND_BASE_URL}/api/routes/alternatives`,
    {
      source: String(sourceNodeId),
      destination: String(destinationNodeId),
      current_route: currentRoute,
      traffic_level: trafficLevel,
      max_alternatives: maxAlternatives,
      request_id: requestId
    },
    { timeout: 35000 }
  );
  return response.data;
};

