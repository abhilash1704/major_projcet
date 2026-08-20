import { Database, Monitor, Map as MapIcon, Navigation, Clock, Server } from "lucide-react";

export const StatusBar = () => {
  const statusItems = [
    { label: "Backend", status: "Connected", icon: Server, color: "bg-success" },
    { label: "Frontend", status: "Connected", icon: Monitor, color: "bg-success" },
    { label: "Database", status: "Connected", icon: Database, color: "bg-success" },
    { label: "GPS", status: "Waiting", icon: Navigation, color: "bg-warning" },
    { label: "Map", status: "Waiting", icon: MapIcon, color: "bg-warning" },
  ];

  return (
    <footer className="h-9 bg-white dark:bg-surface-dark border-t border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 text-xs font-medium text-slate-500 dark:text-slate-400 z-30 shrink-0">
      <div className="flex items-center gap-4 lg:gap-6 overflow-x-auto no-scrollbar py-1">
        {statusItems.map((item, idx) => (
          <div key={idx} className="flex items-center gap-2 whitespace-nowrap">
            <span className={`w-2 h-2 rounded-full ${item.color} animate-pulse`}></span>
            <span className="text-slate-600 dark:text-slate-400">{item.label}:</span>
            <span className="font-semibold text-slate-900 dark:text-slate-200">{item.status}</span>
          </div>
        ))}
      </div>
      
      <div className="flex items-center gap-2 shrink-0 ml-4 pl-4 border-l border-slate-200 dark:border-slate-700/60 text-slate-600 dark:text-slate-300 font-mono text-xs">
        <Clock size={13} className="text-slate-400" />
        <span>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
      </div>
    </footer>
  );
};
