import { Navigation, Loader2 } from "lucide-react";
import { useState } from "react";
import { useGeolocation } from "../hooks/useGeolocation";
import { useMapInstance } from "../hooks/useMapInstance";
import { useNavigationEngine } from "../hooks/useNavigationEngine";
import { Toast } from "../../../components/common/Toast";

export const LocateMeButton = () => {
  const { getCurrentLocation, loading } = useGeolocation();
  const { flyTo } = useMapInstance();
  const { setUserLocation } = useNavigationEngine();
  const [deniedMessage, setDeniedMessage] = useState(null);

  const handleLocate = () => {
    setDeniedMessage(null);
    getCurrentLocation(
      (userCoords) => {
        setUserLocation(userCoords);
        flyTo(userCoords, 15);
      },
      (error) => {
        setDeniedMessage("Location access denied. Map remaining on Bangalore.");
        setTimeout(() => setDeniedMessage(null), 4000);
      }
    );
  };

  return (
    <div className="relative">
      <button
        onClick={handleLocate}
        disabled={loading}
        className="w-10 h-10 bg-white dark:bg-surface-dark rounded-xl shadow-md border border-slate-200 dark:border-slate-800 flex items-center justify-center text-primary hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer pointer-events-auto"
        title="Locate Me"
      >
        {loading ? (
          <Loader2 size={18} className="animate-spin text-primary" />
        ) : (
          <Navigation size={18} />
        )}
      </button>

      <Toast message={deniedMessage} type="error" isVisible={!!deniedMessage} />
    </div>
  );
};
