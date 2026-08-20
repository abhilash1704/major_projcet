import { MapView } from "./MapView";
import { OverlayManager } from "./OverlayManager";

export const NavigationWorkspace = ({ children }) => {
  return (
    <div className="relative w-full h-full overflow-hidden flex-1 flex flex-col">
      <MapView />
      <OverlayManager>{children}</OverlayManager>
    </div>
  );
};
