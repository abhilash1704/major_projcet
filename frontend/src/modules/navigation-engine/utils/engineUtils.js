/**
 * Utility functions for the Navigation Engine
 */
export const formatCoords = (lat, lng) => {
  if (lat == null || lng == null) return "N/A";
  return `${lat.toFixed(4)}°, ${lng.toFixed(4)}°`;
};

export const clampZoom = (zoom, min = 3, max = 19) => {
  return Math.min(Math.max(zoom, min), max);
};
