import { useState, useCallback, useRef } from "react";
import { locationSearchService } from "../services/locationSearchService";

const DEBOUNCE_MS = 350;
const MIN_LENGTH = 3;

/**
 * useLocationSearch
 *
 * Reusable hook for a single search input field (source or destination).
 * Manages debounced Nominatim queries, results, loading, and error state.
 * Cancels stale in-flight requests when the query changes quickly.
 *
 * Does NOT manage text state — the parent (useSearchPanel) owns that.
 */
export const useLocationSearch = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Refs for debounce timer and in-flight AbortController
  const debounceTimer = useRef(null);
  const abortControllerRef = useRef(null);

  /**
   * search(query)
   *
   * Debounces the query, cancels any previous in-flight request, then
   * calls Nominatim. Short queries are cleared immediately.
   */
  const search = useCallback((query) => {
    // Clear previous debounce
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // Too short → clear results immediately, no request
    if (!query || query.trim().length < MIN_LENGTH) {
      setResults([]);
      setError(null);
      setLoading(false);
      return;
    }

    // Show loading immediately so the UI feels responsive
    setLoading(true);
    setError(null);

    debounceTimer.current = setTimeout(async () => {
      // Cancel the previous in-flight request (stale)
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const data = await locationSearchService.searchLocations(
          query,
          controller.signal
        );
        setResults(data);
        setError(data.length === 0 ? "No locations found. Try a different search." : null);
      } catch (err) {
        if (err.name === "AbortError") {
          // Request was cancelled by a newer query — do nothing
          return;
        }

        // Network failure or Nominatim error
        if (!navigator.onLine) {
          setError("No internet connection. Please check your network.");
        } else {
          setError("Could not reach the location service. Please try again.");
        }
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);
  }, []);

  /**
   * clearResults()
   * Clears the dropdown and cancels any pending request.
   */
  const clearResults = useCallback(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setResults([]);
    setError(null);
    setLoading(false);
  }, []);

  return { results, loading, error, search, clearResults };
};
