import { ArrowUpDown } from "lucide-react";

export const SwapButton = ({ onSwap }) => {
  return (
    <button
      onClick={onSwap}
      className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700/80 text-slate-600 dark:text-slate-300 hover:text-primary dark:hover:text-primary hover:bg-slate-200 dark:hover:bg-slate-700 transition-all shadow-xs pointer-events-auto shrink-0"
      title="Swap Source & Destination"
    >
      <ArrowUpDown size={16} />
    </button>
  );
};
