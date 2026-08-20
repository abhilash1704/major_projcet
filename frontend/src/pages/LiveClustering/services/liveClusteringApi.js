/**
 * liveClusteringApi.js — Replay, DBSCAN Vehicle Clustering & Evaluation API Service
 */

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:5000";
const BASE_URL = `${BACKEND_BASE_URL}/api/live-clustering`;

async function safeFetch(url, options = {}) {
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        msg = body.error || body.message || msg;
      } catch { /* non-JSON */ }
      throw new Error(msg);
    }
    return res.json();
  } catch (err) {
    if (err.name === "TypeError" || (err.message && err.message.toLowerCase().includes("fetch"))) {
      throw new Error("Live Clustering API service is temporarily unavailable.");
    }
    throw err;
  }
}

export async function searchBengaluruLocation(query) {
  const q = encodeURIComponent(query.trim());
  const data = await safeFetch(`${BASE_URL}/search-area?q=${q}`);
  return data.results ?? [];
}

export async function analyzeArea(area, radiusMeters = 1000) {
  return safeFetch(`${BASE_URL}/analyze-area`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      latitude:      area.latitude,
      longitude:     area.longitude,
      radius_meters: radiusMeters,
      name:          area.name,
      area_id:       area.id,
      source:        area.source || "preset",
    }),
  });
}

export async function generateTrajectories(params = {}) {
  return safeFetch(`${BASE_URL}/trajectory/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function startReplay() {
  return safeFetch(`${BASE_URL}/trajectory/start`, { method: "POST" });
}

export async function pauseReplay() {
  return safeFetch(`${BASE_URL}/trajectory/pause`, { method: "POST" });
}

export async function stopReplay() {
  return safeFetch(`${BASE_URL}/trajectory/stop`, { method: "POST" });
}

export async function setReplaySpeed(speed = 1.0) {
  return safeFetch(`${BASE_URL}/trajectory/speed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speed }),
  });
}

export async function fetchSnapshot() {
  return safeFetch(`${BASE_URL}/snapshot`);
}

export async function fetchTrajectorySnapshot() {
  return safeFetch(`${BASE_URL}/trajectory/snapshot`);
}

export async function fetchVehicleClusters() {
  return safeFetch(`${BASE_URL}/vehicle-clusters`);
}

export async function fetchRoadDensity() {
  return safeFetch(`${BASE_URL}/road-density`);
}

export async function fetchEvaluation() {
  return safeFetch(`${BASE_URL}/evaluation`);
}

export async function fetchRealTraffic(area, radiusMeters = 1000) {
  return safeFetch(`${BASE_URL}/traffic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      latitude:      area?.latitude,
      longitude:     area?.longitude,
      radius_meters: radiusMeters,
    }),
  });
}
