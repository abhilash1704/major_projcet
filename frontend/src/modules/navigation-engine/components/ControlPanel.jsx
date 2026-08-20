import { LocateMeButton } from "./LocateMeButton";
import { ResetViewButton } from "./ResetViewButton";
import { ZoomControls } from "./ZoomControls";

export const ControlPanel = () => {
  return (
    <div className="absolute bottom-6 left-6 flex flex-col gap-2 z-[1000] pointer-events-auto">
      <LocateMeButton />
      <ResetViewButton />
      <ZoomControls />
    </div>
  );
};
