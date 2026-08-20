import { SearchPanel } from "../../../search/components/SearchPanel";

/**
 * SearchOverlay — Phase 4.1
 * Renders the floating location search panel over the map.
 * Positioned top-left; compact on mobile so it never covers the full map.
 */
export const SearchOverlay = () => {
  return (
    <div className="absolute top-4 left-4 sm:top-5 sm:left-5 z-[1000] pointer-events-auto w-[calc(100vw-2rem)] max-w-[340px] sm:max-w-[400px]">
      <SearchPanel />
    </div>
  );
};
