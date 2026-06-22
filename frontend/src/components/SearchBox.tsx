import React, { useState, useEffect, useRef } from 'react';
import type { KeyboardEvent } from 'react';
import { Search, Loader2, HelpCircle, HardDrive } from 'lucide-react';
import { fetchSuggestions, submitSearch, debugCache } from '../services/api';
import type { SuggestionItem } from '../services/api';

interface SearchBoxProps {
  onSearchExecuted: (query: string) => void;
  onLogRoute: (message: string) => void;
}

export const SearchBox: React.FC<SearchBoxProps> = ({ onSearchExecuted, onLogRoute }) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [focused, setFocused] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [routingInfo, setRoutingInfo] = useState<{ node: string; hit: boolean } | null>(null);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceTimer = useRef<number | null>(null);

  // Handle outside clicks to close dropdown
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setFocused(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  // Fetch suggestions and routing info when query changes
  useEffect(() => {
    if (debounceTimer.current) {
      window.clearTimeout(debounceTimer.current);
    }

    const trimmed = query.trim();
    if (!trimmed) {
      setSuggestions([]);
      setRoutingInfo(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    
    // Fetch cache debug routing info instantly (without debounce)
    debugCache(trimmed)
      .then(info => {
        setRoutingInfo({ node: info.cache_node, hit: info.cache_hit });
        onLogRoute(`Key "${trimmed}" hashed and routed to [${info.cache_node}] (Cache ${info.cache_hit ? 'HIT' : 'MISS'})`);
      })
      .catch(() => {});

    // Debounce the suggestions API call by 300ms
    debounceTimer.current = window.setTimeout(async () => {
      try {
        const res = await fetchSuggestions(trimmed);
        setSuggestions(res.suggestions);
      } catch (err) {
        console.error('Error fetching suggestions', err);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => {
      if (debounceTimer.current) window.clearTimeout(debounceTimer.current);
    };
  }, [query, onLogRoute]);

  const handleExecuteSearch = async (searchQuery: string) => {
    const finalQuery = searchQuery.trim();
    if (!finalQuery) return;

    setQuery(finalQuery);
    setFocused(false);
    
    try {
      onLogRoute(`Submitting search query: "${finalQuery}" -> Pushed to in-memory batch queue`);
      await submitSearch(finalQuery);
      onSearchExecuted(finalQuery);
    } catch (err) {
      console.error('Error submitting search', err);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex(prev => (prev < suggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex(prev => (prev > 0 ? prev - 1 : suggestions.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < suggestions.length) {
        handleExecuteSearch(suggestions[activeIndex].query);
      } else {
        handleExecuteSearch(query);
      }
    } else if (e.key === 'Escape') {
      setFocused(false);
    }
  };

  const highlightMatch = (text: string, prefix: string) => {
    if (!prefix) return <span>{text}</span>;
    const lowerText = text.toLowerCase();
    const lowerPrefix = prefix.toLowerCase();
    
    if (lowerText.startsWith(lowerPrefix)) {
      const match = text.slice(0, prefix.length);
      const rest = text.slice(prefix.length);
      return (
        <span>
          <span className="text-white font-bold">{match}</span>
          <span className="text-slate-400 font-normal">{rest}</span>
        </span>
      );
    }
    return <span>{text}</span>;
  };

  return (
    <div ref={containerRef} className="w-full max-w-2xl relative">
      <div className="relative group">
        {/* Glow border container */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-brand-500 to-purple-600 rounded-2xl blur opacity-30 group-focus-within:opacity-80 transition duration-300"></div>
        
        {/* Input Bar */}
        <div className="relative flex items-center bg-slate-900 border border-slate-800 rounded-2xl px-5 py-4 focus-within:border-slate-700">
          <Search className="text-slate-400 mr-4 w-6 h-6 flex-shrink-0" />
          <input
            type="text"
            value={query}
            onChange={e => {
              setQuery(e.target.value);
              setActiveIndex(-1);
              setFocused(true);
            }}
            onFocus={() => setFocused(true)}
            onKeyDown={handleKeyDown}
            placeholder="Type your search query..."
            className="bg-transparent text-white text-lg placeholder-slate-500 outline-none w-full font-sans"
          />
          {loading && <Loader2 className="animate-spin text-brand-500 ml-4 w-5 h-5 flex-shrink-0" />}
        </div>
      </div>

      {/* Real-time Consistent Hashing Routing Status indicator */}
      {routingInfo && (
        <div className="mt-2.5 px-4 py-1.5 rounded-lg text-xs font-mono flex items-center gap-2 border bg-slate-900/50 backdrop-blur border-slate-800 text-slate-400">
          <HardDrive className="w-3.5 h-3.5 text-brand-400" />
          <span>Consistent Hashing:</span>
          <span className="text-brand-300 font-bold">{routingInfo.node}</span>
          <span>owns prefix</span>
          <span className="text-purple-400 font-bold">"{query}"</span>
          <span className="mx-1">|</span>
          <span>Cache:</span>
          <span className={`font-semibold ${routingInfo.hit ? 'text-emerald-400' : 'text-amber-400'}`}>
            {routingInfo.hit ? 'HIT 🟢' : 'MISS 🟡'}
          </span>
        </div>
      )}

      {/* Autocomplete Suggestion Dropdown */}
      {focused && (suggestions.length > 0 || (query.trim() && !loading)) && (
        <div className="absolute w-full mt-2 bg-slate-900/95 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-2 duration-200">
          {suggestions.length > 0 ? (
            <ul className="py-2">
              {suggestions.map((item, idx) => (
                <li
                  key={idx}
                  onClick={() => handleExecuteSearch(item.query)}
                  onMouseEnter={() => setActiveIndex(idx)}
                  className={`flex items-center justify-between px-6 py-3 cursor-pointer select-none transition-colors ${
                    idx === activeIndex 
                      ? 'bg-brand-950/40 text-white' 
                      : 'text-slate-300 hover:bg-slate-800/40 hover:text-white'
                  }`}
                >
                  <div className="flex items-center">
                    <Search className="w-4 h-4 text-slate-500 mr-4" />
                    <span className="text-base font-sans">
                      {highlightMatch(item.query, query)}
                    </span>
                  </div>
                  <span className="text-xs font-mono font-medium text-slate-500 bg-slate-950/80 px-2 py-0.5 rounded border border-slate-800/60">
                    {item.count.toLocaleString()} searches
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-6 py-5 text-center text-slate-500 flex items-center justify-center gap-2">
              <HelpCircle className="w-4 h-4" />
              <span>No recommendations found matching prefix</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
