import { MapPin, Navigation, ArrowUpDown, Crosshair } from "lucide-react";
import { IconButton } from "../../../modules/shared/components/IconButton";
import { Button } from "../../../components/common/Button";

export const SearchPanel = () => {
  return (
    <div className="bg-white dark:bg-surface-dark w-full max-w-sm rounded-2xl shadow-float p-4 pointer-events-auto border border-slate-100 dark:border-slate-800 absolute top-6 left-6 z-10 animate-fade-in">
      <div className="flex gap-3 relative">
        {/* Timeline dots */}
        <div className="flex flex-col items-center justify-between py-3 px-1">
          <div className="w-2 h-2 rounded-full border-2 border-primary"></div>
          <div className="flex-1 w-px bg-slate-200 dark:bg-slate-700 my-1"></div>
          <div className="w-2 h-2 rounded-full bg-danger"></div>
        </div>
        
        <div className="flex-1 space-y-3">
          <div className="relative">
            <input 
              type="text" 
              placeholder="Choose starting point" 
              className="w-full bg-slate-50 dark:bg-slate-800/50 border border-transparent focus:border-primary focus:bg-white dark:focus:bg-surface-dark px-3 py-2 rounded-xl text-sm outline-none transition-all placeholder:text-slate-400 dark:text-slate-200"
            />
          </div>
          <div className="relative">
            <input 
              type="text" 
              placeholder="Choose destination" 
              className="w-full bg-slate-50 dark:bg-slate-800/50 border border-transparent focus:border-primary focus:bg-white dark:focus:bg-surface-dark px-3 py-2 rounded-xl text-sm outline-none transition-all placeholder:text-slate-400 dark:text-slate-200"
            />
          </div>
        </div>

        <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2">
          <IconButton icon={ArrowUpDown} variant="solid" className="h-8 w-8 !p-1.5 shadow-sm" />
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <IconButton icon={Crosshair} variant="ghost" className="text-primary hover:text-primary-hover hover:bg-primary-light dark:hover:bg-primary-hover/20" />
        <Button className="flex-1 text-sm py-2">Find Route</Button>
      </div>
    </div>
  );
};
