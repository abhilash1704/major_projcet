import { useCallback } from "react";
import { useNavigationEngineContext } from "../context/NavigationEngineContext";
import { overlayService } from "../services/overlayService";

export const useOverlays = () => {
  const { visibleOverlays, setVisibleOverlays } = useNavigationEngineContext();

  const toggleOverlay = useCallback((overlayName) => {
    setVisibleOverlays((prev) => overlayService.toggleOverlay(prev, overlayName));
  }, [setVisibleOverlays]);

  const isOverlayActive = useCallback(
    (overlayName) => !!visibleOverlays[overlayName],
    [visibleOverlays]
  );

  return { visibleOverlays, toggleOverlay, isOverlayActive };
};
