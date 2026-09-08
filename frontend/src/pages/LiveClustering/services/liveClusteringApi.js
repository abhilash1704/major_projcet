/**
 * liveClusteringApi.js — Replay, DBSCAN Vehicle Clustering & Evaluation API Service
 * Routes all operations through the central apiClient.
 */
import { apiClient, TIMEOUT_BUDGETS } from "../../../services/api";

const BASE_PREFIX = "/api/live-clustering";

export async function searchBengaluruLocation(query, signal = null) {
  const q = encodeURIComponent(query.trim());
  const response = await apiClient.get(`${BASE_PREFIX}/search-area?q=${q}`, {
    timeout: TIMEOUT_BUDGETS.GEOCODING,
    signal: signal || undefined,
  });
  return response.data.results ?? [];
}

export async function analyzeArea(area, radiusMeters = 1000, signal = null) {
  const response = await apiClient.post(
    `${BASE_PREFIX}/analyze-area`,
    {
      latitude:      area.latitude,
      longitude:     area.longitude,
      radius_meters: radiusMeters,
      name:          area.name,
      area_id:       area.id,
      source:        area.source || "preset",
    },
    {
      timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
      signal: signal || undefined,
      operationKey: "live_clustering_analyze",
    }
  );
  return response.data;
}

export async function generateTrajectories(params = {}, signal = null) {
  const response = await apiClient.post(`${BASE_PREFIX}/trajectory/generate`, params, {
    timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
    signal: signal || undefined,
  });
  return response.data;
}

export async function startReplay(signal = null) {
  const response = await apiClient.post(`${BASE_PREFIX}/trajectory/start`, {}, {
    timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
    signal: signal || undefined,
  });
  return response.data;
}

export async function pauseReplay(signal = null) {
  const response = await apiClient.post(`${BASE_PREFIX}/trajectory/pause`, {}, {
    timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
    signal: signal || undefined,
  });
  return response.data;
}

export async function stopReplay(signal = null) {
  const response = await apiClient.post(`${BASE_PREFIX}/trajectory/stop`, {}, {
    timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
    signal: signal || undefined,
  });
  return response.data;
}

export async function setReplaySpeed(speed = 1.0, signal = null) {
  const response = await apiClient.post(
    `${BASE_PREFIX}/trajectory/speed`,
    { speed },
    { timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING, signal: signal || undefined }
  );
  return response.data;
}

export async function fetchSnapshot(signal = null) {
  const response = await apiClient.get(`${BASE_PREFIX}/snapshot`, {
    timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
    signal: signal || undefined,
  });
  return response.data;
}

export async function fetchTrajectorySnapshot(signal = null) {
  const response = await apiClient.get(`${BASE_PREFIX}/trajectory/snapshot`, {
    timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
    signal: signal || undefined,
  });
  return response.data;
}

export async function fetchVehicleClusters(signal = null) {
  const response = await apiClient.get(`${BASE_PREFIX}/vehicle-clusters`, {
    timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
    signal: signal || undefined,
  });
  return response.data;
}

export async function fetchRoadDensity(signal = null) {
  const response = await apiClient.get(`${BASE_PREFIX}/road-density`, {
    timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
    signal: signal || undefined,
  });
  return response.data;
}

export async function fetchEvaluation(signal = null) {
  const response = await apiClient.get(`${BASE_PREFIX}/evaluation`, {
    timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
    signal: signal || undefined,
  });
  return response.data;
}

export async function fetchRealTraffic(area, radiusMeters = 1000, signal = null) {
  const response = await apiClient.post(
    `${BASE_PREFIX}/traffic`,
    {
      latitude:      area?.latitude,
      longitude:     area?.longitude,
      radius_meters: radiusMeters,
    },
    {
      timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
      signal: signal || undefined,
    }
  );
  return response.data;
}
