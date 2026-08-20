import { MapPin, Compass, Navigation } from "lucide-react";

export const EmptyWorkspace = () => {
  return (
    <div className="flex-1 h-full w-full relative flex flex-col items-center justify-center bg-[#F8FAFC] dark:bg-[#121316] overflow-hidden select-none">
      {/* Subtle Cartography Map Grid Background */}
      <div 
        className="absolute inset-0 opacity-[0.04] dark:opacity-[0.03]" 
        style={{ 
          backgroundImage: 'linear-gradient(#1A73E8 1px, transparent 1px), linear-gradient(90deg, #1A73E8 1px, transparent 1px)', 
          backgroundSize: '48px 48px' 
        }}
      />
      
      {/* Concentric Circles Effect */}
      <div className="absolute w-[500px] h-[500px] rounded-full border border-primary/10 dark:border-primary/5 pointer-events-none animate-pulse"></div>
      <div className="absolute w-[300px] h-[300px] rounded-full border border-primary/20 dark:border-primary/10 pointer-events-none"></div>

      {/* Centered Illustration Placeholder & Card */}
      <div className="relative z-10 flex flex-col items-center text-center max-w-md px-6 py-10 bg-white/80 dark:bg-surface-dark/80 backdrop-blur-md rounded-3xl border border-slate-200/80 dark:border-slate-800 shadow-xl shadow-slate-200/50 dark:shadow-none animate-fade-in">
        {/* Animated Map Badge Icon */}
        <div className="relative mb-6">
          <div className="w-20 h-20 bg-primary/10 dark:bg-primary/20 rounded-2xl flex items-center justify-center text-primary shadow-inner">
            <Compass size={42} className="animate-spin-slow" />
          </div>
          <div className="absolute -top-1 -right-1 w-6 h-6 bg-primary text-white rounded-full flex items-center justify-center shadow-md">
            <MapPin size={14} />
          </div>
        </div>

        <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight mb-2">
          Interactive Navigation Map
        </h2>
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400 max-w-xs leading-relaxed">
          The live map engine will be integrated in <span className="text-primary font-semibold">Sprint 3</span>.
        </p>

        <div className="mt-6 flex items-center gap-2 px-3.5 py-1.5 bg-slate-100 dark:bg-slate-800/80 rounded-full text-xs font-semibold text-slate-600 dark:text-slate-300">
          <Navigation size={13} className="text-primary" />
          <span>Vehicle Clustering & Traffic Engine Ready</span>
        </div>
      </div>
    </div>
  );
};
