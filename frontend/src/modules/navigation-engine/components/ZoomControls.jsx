import { Plus, Minus } from "lucide-react";
import { useMapInstance } from "../hooks/useMapInstance";

export const ZoomControls = () => {
  const { zoomIn, zoomOut } = useMapInstance();

  return (
    <div className="flex flex-col rounded-xl overflow-hidden shadow-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-surface-dark pointer-events-auto">
      <button
        onClick={zoomIn}
        className="w-10 h-10 flex items-center justify-center text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors border-b border-slate-100 dark:border-slate-800 cursor-pointer"
        title="Zoom In"
      >
        <Plus size={18} />
      </button>
      <button
        onClick={zoomOut}
        className="w-10 h-10 flex items-center justify-center text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
        title="Zoom Out"
      >
        <Minus size={18} />
      </button>
    </div>
  );
};
