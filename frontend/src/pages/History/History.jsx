import { useState, useEffect, useCallback, useRef } from "react";
import { AppLayout } from "../../modules/layout/components/AppLayout";
import { PageContainer } from "../../modules/shared/components/PageContainer";
import { SectionHeader } from "../../modules/layout/components/SectionHeader";
import { HistoryFilters } from "./HistoryFilters";
import { HistoryItem } from "./HistoryItem";
import { HistoryEmptyState } from "./HistoryEmptyState";
import { historyService } from "../../services/historyService";
import { Loader2 } from "lucide-react";

export const History = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const abortControllerRef = useRef(null);
  const reqSequenceRef = useRef(0);
  
  const [filters, setFilters] = useState({
    algorithm: "All",
    routing_mode: "All",
    traffic_level: "All",
    search: ""
  });

  const fetchHistory = useCallback(async (currentPage, currentFilters) => {
    // Cancel in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const seq = ++reqSequenceRef.current;

    try {
      setLoading(true);
      setError(null);
      
      const res = await historyService.getHistory({
        page: currentPage,
        limit: 20,
        algorithm: currentFilters.algorithm !== "All" ? currentFilters.algorithm : undefined,
        routing_mode: currentFilters.routing_mode !== "All" ? currentFilters.routing_mode : undefined,
        traffic_level: currentFilters.traffic_level !== "All" ? currentFilters.traffic_level : undefined,
        search: currentFilters.search || undefined,
      }, controller.signal);
      
      if (seq !== reqSequenceRef.current) return; // Discard stale response

      if (res.success) {
        if (currentPage === 1) {
          setItems(res.items);
        } else {
          setItems(prev => [...prev, ...res.items]);
        }
        setHasNext(res.has_next);
      }
    } catch (err) {
      if (err.name === "AbortError" || err.isCancelled) return;
      if (seq !== reqSequenceRef.current) return;
      console.error(err);
      setError("Unable to load trip history.");
    } finally {
      if (seq === reqSequenceRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    setPage(1);
    fetchHistory(1, filters);
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [filters, fetchHistory]);

  const loadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchHistory(nextPage, filters);
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this trip?")) return;
    try {
      await historyService.deleteHistory(id);
      setItems(prev => prev.filter(item => item.id !== id));
    } catch (err) {
      console.error(err);
      alert("Failed to delete trip.");
    }
  };

  return (
    <AppLayout>
      <PageContainer>
        <SectionHeader title="HISTORY" description="Your recent routes and trips" />
        
        <div className="flex flex-col h-full gap-6 max-w-4xl mx-auto w-full pt-4">
          <HistoryFilters filters={filters} onFilterChange={setFilters} />
          
          <div className="flex-1 overflow-y-auto">
            {error && (
              <div className="text-red-400 p-4 bg-red-900/20 rounded-md border border-red-500/20 flex flex-col items-center">
                <p>{error}</p>
                <button onClick={() => fetchHistory(1, filters)} className="mt-2 px-3 py-1 bg-red-900/50 hover:bg-red-800 text-sm rounded transition-colors">Retry</button>
              </div>
            )}
            
            {!loading && items.length === 0 && !error && (
              <HistoryEmptyState hasFilters={filters.search !== "" || filters.algorithm !== "All" || filters.routing_mode !== "All" || filters.traffic_level !== "All"} />
            )}

            <div className="flex flex-col gap-4 pb-12">
              {items.map(item => (
                <HistoryItem key={item.id} item={item} onDelete={() => handleDelete(item.id)} />
              ))}
              
              {hasNext && (
                <button 
                  onClick={loadMore} 
                  disabled={loading}
                  className="mt-6 px-4 py-2 bg-slate-800/80 hover:bg-slate-700 text-slate-200 rounded-md text-sm mx-auto transition-colors"
                >
                  {loading ? "Loading..." : "Load More"}
                </button>
              )}
            </div>

            {loading && items.length === 0 && (
              <div className="flex justify-center items-center py-12">
                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                <span className="ml-3 text-slate-400 font-medium">Loading history...</span>
              </div>
            )}
          </div>
        </div>
      </PageContainer>
    </AppLayout>
  );
};
