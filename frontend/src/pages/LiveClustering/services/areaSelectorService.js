/**
 * areaSelectorService.js — Live Clustering Phase 4
 *
 * Isolated service for area selection operations:
 *   - searchBengaluruLocation: geocodes via backend Nominatim proxy.
 *   - analyzeArea: calls /api/live-clustering/area-snapshot.
 *
 * Does NOT interact with NavigationEngineContext, routing, or A*.
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
      } catch { /* non-JSON response */ }
      throw new Error(msg);
    }
    return res.json();
  } catch (err) {
    if (err.name === "TypeError" || (err.message && err.message.toLowerCase().includes("fetch"))) {
      throw new Error("Live Clustering service is temporarily unavailable.");
    }
    throw err;
  }
}

/**
 * Geocode a Bengaluru location via the backend Nominatim proxy.
 * @param {string} query - User search string, e.g. "Koramangala"
 * @returns {Promise<Array<{name, full_name, latitude, longitude, source}>>}
 */
export async function searchBengaluruLocation(query) {
  const q = encodeURIComponent(query.trim());
  const data = await safeFetch(`${BASE_URL}/search-area?q=${q}`);
  return data.results ?? [];
}

/**
 * Request an area-snapshot analysis from the backend.
 * @param {Object} area - { name, latitude, longitude }
 * @param {number} radiusMeters - 500 | 1000 | 2000
 * @returns {Promise<Object>} area-snapshot response
 */
export async function analyzeArea(area, radiusMeters = 1000) {
  return safeFetch(`${BASE_URL}/area-snapshot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      latitude:  area.latitude,
      longitude: area.longitude,
      radius_m:  radiusMeters,
      name:      area.name,
    }),
  });
}


