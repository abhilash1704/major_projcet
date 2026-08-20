import { useMap } from "react-leaflet";
import { useCallback } from "react";
import { ENGINE_CONFIG } from "../constants/engineConstants";

export const useMapInstance = () => {
  const map = useMap();

  const resetView = useCallback(() => {
    map.flyTo(ENGINE_CONFIG.DEFAULT_CENTER, ENGINE_CONFIG.DEFAULT_ZOOM, {
      duration: 1.2,
    });
  }, [map]);

  const zoomIn = useCallback(() => {
    map.zoomIn();
  }, [map]);

  const zoomOut = useCallback(() => {
    map.zoomOut();
  }, [map]);

  const flyTo = useCallback((coords, zoomLevel = 15) => {
    map.flyTo(coords, zoomLevel, { duration: 1.5 });
  }, [map]);

  return { map, resetView, zoomIn, zoomOut, flyTo };
};
