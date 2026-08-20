/**
 * Overlay Service
 * Service layer for managing UI overlay registrations and visibility states
 */
export const overlayService = {
  getDefaultOverlays() {
    return {
      search: true,
      navigation: true,
      traffic: true,
      vehicle: true,
      cluster: true,
      route: true,
      system: true,
    };
  },

  toggleOverlay(activeOverlays, overlayName) {
    return {
      ...activeOverlays,
      [overlayName]: !activeOverlays[overlayName],
    };
  },
};
