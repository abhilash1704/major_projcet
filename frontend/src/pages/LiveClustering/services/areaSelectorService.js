/**
 * areaSelectorService.js — Live Clustering Area Selection Service
 * Routes through the central apiClient.
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
    `${BASE_PREFIX}/area-snapshot`,
    {
      latitude:  area.latitude,
      longitude: area.longitude,
      radius_m:  radiusMeters,
      name:      area.name,
    },
    {
      timeout: TIMEOUT_BUDGETS.LIVE_CLUSTERING,
      signal: signal || undefined,
      operationKey: "area_snapshot_analyze",
    }
  );
  return response.data;
}
