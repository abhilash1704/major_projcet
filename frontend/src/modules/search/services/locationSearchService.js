/**
 * locationSearchService
 *
 * Responsible for all Nominatim geocoding API calls.
 * All fetch logic stays here — no API code in UI components or hooks.
 *
 * Nominatim usage policy:
 *   - Must include a descriptive User-Agent header.
 *   - Max 1 request/second (enforced by debounce in the hook layer).
 *   - No bulk or automated requests.
 */

const NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search";
const USER_AGENT = "AlgoRoutes/1.0 (Navigation Engine; contact=algoroutes-dev)";
const MIN_QUERY_LENGTH = 3;
const REQUEST_TIMEOUT_MS = 8000;

/**
 * Normalises a raw Nominatim result into a consistent shape.
 * @param {object} raw - One element from the Nominatim JSON array.
 * @returns {object} Normalised location object.
 */
function normalise(raw) {
  return {
    placeId: String(raw.place_id),
    displayName: raw.display_name,
    latitude: parseFloat(raw.lat),
    longitude: parseFloat(raw.lon),
    type: raw.type ?? raw.class ?? "place",
    address: raw.address ?? {},
  };
}

/**
 * Searches Nominatim for locations matching `query`.
 *
 * @param {string} query - The user-typed search text.
 * @param {AbortSignal} [signal] - Optional AbortController signal for cancellation.
 * @returns {Promise<Array>} Normalised location results (up to 5).
 *
 * Throws with `.name === "AbortError"` when the request is cancelled — callers
 * should check for this and skip error handling in that case.
 */
async function searchLocations(query, signal) {
  if (!query || query.trim().length < MIN_QUERY_LENGTH) {
    return [];
  }

  const params = new URLSearchParams({
    q: query.trim(),
    format: "json",
    limit: "5",
    addressdetails: "1",
  });

  const url = `${NOMINATIM_BASE}?${params.toString()}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  // If the caller provides their own signal, wire it up too
  const combinedSignal = signal
    ? combineSignals(signal, controller.signal)
    : controller.signal;

  try {
    const response = await fetch(url, {
      headers: {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en",
      },
      signal: combinedSignal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Nominatim responded with status ${response.status}`);
    }

    const data = await response.json();

    if (!Array.isArray(data)) {
      throw new Error("Unexpected response format from Nominatim.");
    }

    return data.map(normalise);
  } catch (err) {
    clearTimeout(timeoutId);
    throw err; // let the hook layer classify AbortError vs real errors
  }
}

/**
 * Merges two AbortSignals so that aborting either one aborts the combined signal.
 */
function combineSignals(sig1, sig2) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  sig1.addEventListener("abort", abort, { once: true });
  sig2.addEventListener("abort", abort, { once: true });
  return controller.signal;
}

export const locationSearchService = { searchLocations };
