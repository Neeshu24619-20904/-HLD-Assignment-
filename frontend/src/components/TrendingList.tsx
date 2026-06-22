import React, { useState, useEffect } from 'react';
import { Flame, RefreshCw } from 'lucide-react';
import { fetchTrending } from '../services/api';
import type { SuggestionItem } from '../services/api';

interface TrendingListProps {
  onTagClick: (query: string) => void;
  refreshTrigger: number;
}

export const TrendingList: React.FC<TrendingListProps> = ({ onTagClick, refreshTrigger }) => {
  const [trending, setTrending] = useState<SuggestionItem[]>([]);
  const [loading, setLoading] = useState(false);

  const loadTrending = async () => {
    setLoading(true);
    try {
      const res = await fetchTrending();
      setTrending(res.trending);
    } catch (err) {
      console.error('Error fetching trending searches', err);
    } finally {
      setLoading(false);
    }
  };

  // Load on mount, when external refresh trigger fires, and set up 1-minute interval
  useEffect(() => {
    loadTrending();

    const interval = setInterval(() => {
      loadTrending();
    }, 60000); // 60 seconds (1 minute)

    return () => clearInterval(interval);
  }, [refreshTrigger]);

  return (
    <div className="w-full max-w-2xl bg-slate-900/40 border border-slate-900 rounded-2xl p-6 backdrop-blur">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Flame className="w-5 h-5 text-amber-500 fill-amber-500 animate-pulse" />
          <h3 className="text-md font-bold uppercase tracking-wider text-slate-400">🔥 Trending Searches</h3>
        </div>
        <button
          onClick={loadTrending}
          disabled={loading}
          className="text-slate-400 hover:text-white transition-colors"
          title="Refresh trending searches"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {trending.length > 0 ? (
        <div className="flex flex-wrap gap-2.5">
          {trending.map((item, idx) => (
            <button
              key={idx}
              onClick={() => onTagClick(item.query)}
              className="px-4 py-2 rounded-xl text-sm font-sans font-medium bg-slate-950/80 border border-slate-850 hover:bg-brand-950/20 hover:border-brand-500/40 text-slate-300 hover:text-brand-300 active:scale-95 transition-all flex items-center gap-2"
            >
              <span>{item.query}</span>
              <span className="text-[10px] font-mono text-slate-500 bg-slate-900 border border-slate-800 px-1.5 py-0.25 rounded-md">
                {item.count >= 1000 ? `${(item.count / 1000).toFixed(0)}k` : item.count}
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="text-center py-4 text-slate-500 text-sm font-sans">
          No trending queries logged in the last week. Submit searches to trend!
        </div>
      )}
    </div>
  );
};
