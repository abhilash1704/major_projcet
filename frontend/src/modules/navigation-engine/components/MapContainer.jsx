import { useState } from "react";
import { MapContainer as LeafletMapContainer, TileLayer } from "react-leaflet";
import { ENGINE_CONFIG } from "../constants/engineConstants";
import { ControlPanel } from "./ControlPanel";
import { LayerManager } from "./LayerManager";
import { CurrentLocationMarker } from "./CurrentLocationMarker";
import { Toast } from "../../../components/common/Toast";
import L from "leaflet";
import "../styles/navigation-engine.css";

// Fix default marker icon issues in Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

export const MapContainer = ({ children }) => {
  const [mapError, setMapError] = useState(null);

  const handleTileError = () => {
    if (!mapError) {
      setMapError("Failed to load map data. Please check your connection.");
      setTimeout(() => setMapError(null), 5000);
    }
  };

  return (
    <div className="w-full h-full relative overflow-hidden z-0">
      <LeafletMapContainer
        center={ENGINE_CONFIG.DEFAULT_CENTER}
        zoom={ENGINE_CONFIG.DEFAULT_ZOOM}
        scrollWheelZoom={true}
        zoomControl={false}
        className="w-full h-full z-0"
      >
        <TileLayer
          attribution={ENGINE_CONFIG.ATTRIBUTION}
          url={ENGINE_CONFIG.TILE_LAYER_URL}
          maxZoom={ENGINE_CONFIG.MAX_ZOOM}
          eventHandlers={{ tileerror: handleTileError }}
        />
        <CurrentLocationMarker />
        <LayerManager />
        <ControlPanel />
        {children}
      </LeafletMapContainer>
      <Toast message={mapError} type="error" isVisible={!!mapError} />
    </div>
  );
};
