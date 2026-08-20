/**
 * Layer Service
 * Service layer for registering, toggling, and managing map layers
 */
export const layerService = {
  getDefaultLayers() {
    return {
      marker: true,
      route: true,
      traffic: true,
      vehicle: true,
      cluster: true,
      selection: true,
    };
  },

  toggleLayer(activeLayers, layerName) {
    return {
      ...activeLayers,
      [layerName]: !activeLayers[layerName],
    };
  },
};
