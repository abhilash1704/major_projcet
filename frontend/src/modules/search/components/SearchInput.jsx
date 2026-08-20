import { MapPin, X, Navigation, Loader2, AlertCircle } from "lucide-react";
import { useState, useRef, useEffect, useCallback } from "react";

/**
 * SearchInput — Phase 4.2
 *
 * A single location search input with a real Nominatim results dropdown.
 * All fetching is done externally (useLocationSearch) — this component only
 * handles rendering and keyboard navigation.
 *
 * Props:
 *   placeholder        – input placeholder text
 *   value              – controlled text value
 *   onChange           – called with new text on every keystroke
 *   onClear            – called when the ✕ button is clicked
 *   onSelectResult     – called with a normalised location object when the
 *                        user picks a suggestion
 *   onSelectCurrentLocation – optional; shows the GPS button in the input
 *   icon               – lucide icon component for the left icon
 *   iconColor          – Tailwind colour class for the icon
 *   results            – array of normalised location objects from Nominatim
 *   loading            – boolean; shows spinner in the dropdown
 *   searchError        – string | null; shown inside the dropdown
 *   aria-label         – accessible label for the input element
 */
export const SearchInput = ({
  placeholder,
  value,
  onChange,
  onClear,
  onSelectResult,
  onSelectCurrentLocation,
  icon: Icon = MapPin,
  iconColor = "text-primary",
  results = [],
  loading = false,
  searchError = null,
  "aria-label": ariaLabel,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const wrapperRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const hasContent = results.length > 0 || loading || searchError;
  const showDropdown = isOpen && hasContent;

  // ── Close on outside click ───────────────────────────────────────────
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setIsOpen(false);
        setActiveIndex(-1);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // ── Reset active index when results change ───────────────────────────
  useEffect(() => {
    setActiveIndex(-1);
  }, [results]);

  // ── Keyboard navigation ───────────────────────────────────────────────
  const handleKeyDown = useCallback(
    (e) => {
      if (!isOpen) {
        if (e.key === "ArrowDown") {
          setIsOpen(true);
        }
        return;
      }

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setActiveIndex((prev) =>
            prev < results.length - 1 ? prev + 1 : prev
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setActiveIndex((prev) => (prev > 0 ? prev - 1 : 0));
          break;
        case "Enter":
          e.preventDefault();
          if (activeIndex >= 0 && results[activeIndex]) {
            handleSelect(results[activeIndex]);
          }
          break;
        case "Escape":
          setIsOpen(false);
          setActiveIndex(-1);
          inputRef.current?.blur();
          break;
        default:
          break;
      }
    },
    [isOpen, results, activeIndex]
  );

  // Scroll active item into view
  useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const item = listRef.current.children[activeIndex];
      if (item) item.scrollIntoView({ block: "nearest" });
    }
  }, [activeIndex]);

  const handleSelect = useCallback(
    (result) => {
      onSelectResult(result);
      setIsOpen(false);
      setActiveIndex(-1);
    },
    [onSelectResult]
  );

  const handleChange = (e) => {
    onChange(e.target.value);
    setIsOpen(true);
    setActiveIndex(-1);
  };

  const handleFocus = () => {
    if (hasContent) setIsOpen(true);
  };

  return (
    <div ref={wrapperRef} className="relative flex-1 pointer-events-auto">
      {/* ── Input row ── */}
      <div className="relative flex items-center">
        <div className={`absolute left-3.5 ${iconColor} pointer-events-none`}>
          <Icon size={16} />
        </div>

        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleChange}
          onFocus={handleFocus}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label={ariaLabel}
          aria-autocomplete="list"
          aria-expanded={showDropdown}
          autoComplete="off"
          className="w-full pl-10 pr-16 py-2.5 bg-slate-50 dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700/80 rounded-xl text-sm font-medium text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
        />

        <div className="absolute right-2 flex items-center gap-1">
          {loading && (
            <Loader2
              size={14}
              className="text-primary animate-spin pointer-events-none"
              aria-label="Searching..."
            />
          )}
          {value && !loading && (
            <button
              onClick={() => {
                onClear();
                setIsOpen(false);
              }}
              className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-200/50 dark:hover:bg-slate-700 transition-colors"
              title="Clear"
              aria-label="Clear input"
            >
              <X size={14} />
            </button>
          )}
          {onSelectCurrentLocation && (
            <button
              onClick={onSelectCurrentLocation}
              className="p-1 text-primary hover:text-primary-dark rounded-lg hover:bg-primary/10 transition-colors"
              title="Use Current Location"
              aria-label="Use current GPS location"
            >
              <Navigation size={14} />
            </button>
          )}
        </div>
      </div>

      {/* ── Dropdown ── */}
      {showDropdown && (
        <div
          className="absolute top-full left-0 right-0 mt-1.5 bg-white dark:bg-surface-dark border border-slate-200 dark:border-slate-700/80 rounded-xl shadow-2xl z-[2000] overflow-hidden animate-fade-in"
          role="listbox"
          aria-label="Location suggestions"
        >
          {/* Loading state */}
          {loading && (
            <div className="px-4 py-3 flex items-center gap-2.5 text-xs text-slate-500 dark:text-slate-400">
              <Loader2 size={13} className="animate-spin text-primary shrink-0" />
              <span>Searching locations…</span>
            </div>
          )}

          {/* Error / empty state */}
          {!loading && searchError && (
            <div className="px-4 py-3 flex items-center gap-2.5 text-xs text-slate-500 dark:text-slate-400">
              <AlertCircle size={13} className="shrink-0 text-slate-400" />
              <span>{searchError}</span>
            </div>
          )}

          {/* Results list */}
          {!loading && !searchError && results.length > 0 && (
            <>
              <div className="px-3 pt-2 pb-1 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                Suggested Locations
              </div>
              <ul ref={listRef} className="max-h-52 overflow-y-auto pb-1">
                {results.map((result, idx) => {
                  const isActive = idx === activeIndex;
                  // Derive short name: text before the first comma
                  const shortName = result.displayName.split(",")[0];
                  const rest = result.displayName.slice(shortName.length + 1).trim();

                  return (
                    <li
                      key={result.placeId}
                      role="option"
                      aria-selected={isActive}
                      onClick={() => handleSelect(result)}
                      onMouseEnter={() => setActiveIndex(idx)}
                      className={`px-3 py-2.5 text-sm cursor-pointer flex items-start gap-2.5 transition-colors ${
                        isActive
                          ? "bg-primary/8 dark:bg-primary/15"
                          : "hover:bg-slate-50 dark:hover:bg-slate-800/60"
                      }`}
                    >
                      <MapPin
                        size={13}
                        className={`mt-0.5 shrink-0 ${
                          isActive ? "text-primary" : "text-slate-400"
                        }`}
                      />
                      <div className="min-w-0">
                        <div className="font-semibold text-slate-800 dark:text-white truncate">
                          {shortName}
                        </div>
                        {rest && (
                          <div className="text-[11px] text-slate-400 dark:text-slate-500 truncate mt-0.5">
                            {rest}
                          </div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
};
