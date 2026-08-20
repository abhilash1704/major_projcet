import { Navigation } from "lucide-react";

export const CurrentLocationButton = ({ onSelect }) => {
  return (
    <button
      onClick={onSelect}
      className="px-3 py-2 text-xs font-semibold text-primary dark:text-primary-light hover:bg-primary/10 rounded-xl transition-colors flex items-center gap-1.5 pointer-events-auto"
      title="Use Current Location"
    >
      <Navigation size={13} />
      <span>My Location</span>
    </button>
  );
};
