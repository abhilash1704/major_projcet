import { Marker, Popup, CircleMarker } from "react-leaflet";
import { useNavigationEngine } from "../hooks/useNavigationEngine";

/**
 * CurrentLocationMarker Component
 * Renders blue marker for user's current location with "You are here." popup
 */
export const CurrentLocationMarker = () => {
  const { userLocation } = useNavigationEngine();

  if (!userLocation) return null;

  return (
    <>
      {/* Outer accuracy/pulse circle */}
      <CircleMarker
        center={userLocation}
        radius={20}
        pathOptions={{
          fillColor: "#1A73E8",
          fillOpacity: 0.15,
          color: "#1A73E8",
          weight: 1.5,
        }}
      />
      {/* Inner location dot */}
      <CircleMarker
        center={userLocation}
        radius={8}
        pathOptions={{
          fillColor: "#1A73E8",
          fillOpacity: 1,
          color: "#ffffff",
          weight: 2.5,
        }}
      />
      {/* Interactive Pin Marker with Popup */}
      <Marker position={userLocation}>
        <Popup autoPan={true}>
          <div className="text-xs font-bold text-slate-800 p-0.5 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span>
            <span>You are here.</span>
          </div>
        </Popup>
      </Marker>
    </>
  );
};
