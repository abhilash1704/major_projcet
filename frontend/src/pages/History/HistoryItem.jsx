import { MapPin, Navigation, Clock, Trash2, Calendar, Route } from "lucide-react";

export const HistoryItem = ({ item, onDelete }) => {
  const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  }) : "Unknown Date";

  const getTrafficColor = (level) => {
    switch (level?.toUpperCase()) {
      case "HIGH": return "text-red-400 bg-red-400/10 border-red-400/20";
      case "MEDIUM": return "text-orange-400 bg-orange-400/10 border-orange-400/20";
      case "LOW": return "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";
      default: return "text-slate-400 bg-slate-400/10 border-slate-400/20";
    }
  };

  return (
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center bg-slate-900/60 p-5 rounded-lg border border-slate-700/50 hover:border-slate-600/60 transition-colors gap-4">
      
      <div className="flex flex-col gap-3 flex-1 min-w-0">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Calendar className="w-3 h-3" />
          <span>{dateStr}</span>
        </div>
        
        <div className="flex items-start gap-3">
          <div className="flex flex-col items-center mt-1">
            <div className="w-2 h-2 rounded-full bg-indigo-400" />
            <div className="w-0.5 h-6 bg-slate-700" />
            <div className="w-2 h-2 rounded-full border-2 border-rose-400 bg-transparent" />
          </div>
          
          <div className="flex flex-col gap-2 min-w-0 flex-1">
            <div className="text-sm font-medium text-slate-200 truncate" title={item.source_name}>
              {item.source_name || "Unknown Source"}
            </div>
            <div className="text-sm font-medium text-slate-200 truncate" title={item.destination_name}>
              {item.destination_name || "Unknown Destination"}
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap md:flex-nowrap items-center gap-3 w-full md:w-auto">
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/80 rounded-md border border-slate-700/50">
          <Route className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-xs font-medium text-slate-300">
            {item.distance_km ? item.distance_km.toFixed(1) : "0.0"} km
          </span>
        </div>
        
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/80 rounded-md border border-slate-700/50">
          <Clock className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-xs font-medium text-slate-300">
            {item.eta_minutes ? Math.round(item.eta_minutes) : "0"} min
          </span>
        </div>

        <div className={`flex items-center px-3 py-1.5 rounded-md border text-xs font-medium ${getTrafficColor(item.traffic_level)}`}>
          {item.traffic_level || "UNKNOWN"}
        </div>
        
        <div className="flex flex-col gap-1 px-3 py-1.5 bg-slate-800/50 rounded-md border border-slate-700/30 text-[10px] text-slate-400 min-w-[90px] text-center">
          <span className="font-semibold uppercase text-slate-300">{item.algorithm === 'astar' ? 'A* Search' : item.algorithm}</span>
          <span className="opacity-80">{item.routing_mode === 'traffic_aware' ? 'Traffic-Aware' : 'Normal'}</span>
        </div>

        <button 
          onClick={onDelete}
          className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-md transition-colors ml-auto md:ml-0"
          title="Delete record"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

    </div>
  );
};
