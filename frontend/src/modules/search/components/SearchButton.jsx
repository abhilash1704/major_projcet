import { Search, Loader2 } from "lucide-react";

export const SearchButton = ({ onClick, isLoading = false }) => {
  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      className="w-full py-2.5 bg-primary hover:bg-primary-dark disabled:opacity-70 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 pointer-events-auto cursor-pointer"
    >
      {isLoading ? (
        <Loader2 size={16} className="animate-spin" />
      ) : (
        <Search size={16} />
      )}
      <span>{isLoading ? "Searching..." : "Search Route"}</span>
    </button>
  );
};
