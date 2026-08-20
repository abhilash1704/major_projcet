import { Search, Filter } from "lucide-react";

export const HistoryFilters = ({ filters, onFilterChange }) => {
  const handleSelect = (key, value) => {
    onFilterChange(prev => ({ ...prev, [key]: value }));
  };

  const handleSearch = (e) => {
    onFilterChange(prev => ({ ...prev, search: e.target.value }));
  };

  return (
    <div className="flex flex-col sm:flex-row gap-4 items-center bg-slate-900/40 p-4 rounded-lg border border-slate-700/50">
      <div className="relative flex-1 w-full">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input 
          type="text" 
          placeholder="Search by location..."
          value={filters.search}
          onChange={handleSearch}
          className="w-full bg-slate-800/80 text-sm text-slate-200 placeholder:text-slate-500 rounded-md pl-9 pr-4 py-2 border border-slate-700/50 focus:outline-none focus:border-indigo-500/50"
        />
      </div>
      
      <div className="flex gap-2 w-full sm:w-auto overflow-x-auto pb-2 sm:pb-0 hide-scrollbar">
        <div className="flex items-center gap-2 px-2 text-slate-400">
          <Filter className="w-4 h-4" />
        </div>
        
        <select 
          value={filters.algorithm}
          onChange={(e) => handleSelect("algorithm", e.target.value)}
          className="bg-slate-800/80 text-xs text-slate-300 rounded-md px-3 py-2 border border-slate-700/50 focus:outline-none focus:border-indigo-500/50 appearance-none"
        >
          <option value="All">All Algorithms</option>
          <option value="astar">A* Search</option>
          <option value="dijkstra">Dijkstra</option>
        </select>

        <select 
          value={filters.routing_mode}
          onChange={(e) => handleSelect("routing_mode", e.target.value)}
          className="bg-slate-800/80 text-xs text-slate-300 rounded-md px-3 py-2 border border-slate-700/50 focus:outline-none focus:border-indigo-500/50 appearance-none"
        >
          <option value="All">All Modes</option>
          <option value="normal">Normal</option>
          <option value="traffic_aware">Traffic-Aware</option>
        </select>
        
        <select 
          value={filters.traffic_level}
          onChange={(e) => handleSelect("traffic_level", e.target.value)}
          className="bg-slate-800/80 text-xs text-slate-300 rounded-md px-3 py-2 border border-slate-700/50 focus:outline-none focus:border-indigo-500/50 appearance-none"
        >
          <option value="All">Any Traffic</option>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
        </select>
      </div>
    </div>
  );
};
