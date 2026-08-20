import { Trash2 } from "lucide-react";

export const ClearButton = ({ onClear }) => {
  return (
    <button
      onClick={onClear}
      className="px-3 py-2 text-xs font-semibold text-slate-500 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-400 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-1.5 pointer-events-auto"
      title="Clear Search Inputs"
    >
      <Trash2 size={13} />
      <span>Clear</span>
    </button>
  );
};
