import { RouteOff, SearchX } from "lucide-react";
import { Link } from "react-router-dom";

export const HistoryEmptyState = ({ hasFilters }) => {
  if (hasFilters) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-slate-900/20 rounded-lg border border-slate-800/50">
        <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mb-4 border border-slate-700">
          <SearchX className="w-8 h-8 text-slate-400" />
        </div>
        <h3 className="text-lg font-medium text-slate-200 mb-2">No matching trips found</h3>
        <p className="text-slate-400 max-w-sm mb-6 text-sm">
          We couldn't find any trips matching your current search or filter criteria.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-slate-900/20 rounded-lg border border-slate-800/50">
      <div className="w-16 h-16 rounded-full bg-indigo-500/10 flex items-center justify-center mb-4 border border-indigo-500/20">
        <RouteOff className="w-8 h-8 text-indigo-400" />
      </div>
      <h3 className="text-lg font-medium text-slate-200 mb-2">No route history yet</h3>
      <p className="text-slate-400 max-w-sm mb-6 text-sm">
        When you search for routes and navigate, your successful trips will appear here automatically.
      </p>
      <Link 
        to="/navigation" 
        className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-md transition-colors shadow-lg shadow-indigo-900/20"
      >
        Calculate a Route
      </Link>
    </div>
  );
};
