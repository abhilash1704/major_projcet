import { useCallback } from "react";
import { useNavigationEngineContext } from "../context/NavigationEngineContext";
import { layerService } from "../services/layerService";

export const useLayers = () => {
  const { visibleLayers, setVisibleLayers } = useNavigationEngineContext();

  const toggleLayer = useCallback((layerName) => {
    setVisibleLayers((prev) => layerService.toggleLayer(prev, layerName));
  }, [setVisibleLayers]);

  const isLayerActive = useCallback(
    (layerName) => !!visibleLayers[layerName],
    [visibleLayers]
  );

  return { visibleLayers, toggleLayer, isLayerActive };
};
