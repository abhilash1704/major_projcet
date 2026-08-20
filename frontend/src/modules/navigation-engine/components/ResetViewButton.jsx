import { RotateCcw } from "lucide-react";
import { useMapInstance } from "../hooks/useMapInstance";

export const ResetViewButton = () => {
  const { resetView } = useMapInstance();

  return (
    <button
      onClick={resetView}
      className="w-10 h-10 bg-white dark:bg-surface-dark rounded-xl shadow-md border border-slate-200 dark:border-slate-800 flex items-center justify-center text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer pointer-events-auto"
      title="Reset View to Bangalore"
    >
      <RotateCcw size={17} />
    </button>
  );
};
