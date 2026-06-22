import React, { useState, useEffect } from 'react';
import { 
  Zap, HardDrive, Database, Server, RefreshCw, BarChart2, Activity
} from 'lucide-react';
import { fetchMetrics, fetchTrending } from '../services/api';
import type { MetricsResponse, SuggestionItem } from '../services/api';

interface AnalyticsDashboardProps {
  routingLogs: string[];
  onClearLogs: () => void;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ routingLogs, onClearLogs }) => {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [rankingTable, setRankingTable] = useState<SuggestionItem[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [mRes, tRes] = await Promise.all([fetchMetrics(), fetchTrending()]);
      setMetrics(mRes);
      setRankingTable(tRes.trending);
    } catch (err) {
      console.error('Error fetching analytics data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Poll every 3 seconds for active live updates during demos
    const interval = setInterval(() => {
      loadData();
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full max-w-6xl space-y-8 animate-in fade-in duration-300">
      {/* Title & Refresh */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <BarChart2 className="w-8 h-8 text-brand-400" />
            Developer Analytics Dashboard
          </h2>
          <p className="text-slate-400 mt-1 text-sm">
            Real-time telemetry measuring consistent hashing, cache hits, latency, and batch write efficiency.
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800 hover:text-white transition-all text-slate-300"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Stats
        </button>
      </div>

      {/* 3 Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Performance */}
        <div className="relative group overflow-hidden bg-slate-900/40 border border-slate-900 rounded-2xl p-6 backdrop-blur">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Zap className="w-24 h-24 text-brand-400" />
          </div>
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-xl bg-brand-950/60 border border-brand-500/20 text-brand-400">
              <Zap className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">Performance Latency</h3>
          </div>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-slate-500 font-sans uppercase">p95 Latency</div>
              <div className="text-4xl font-extrabold font-mono text-brand-300 mt-1">
                {metrics ? `${metrics.p95_latency_ms.toFixed(2)}` : '0.00'}<span className="text-lg font-sans font-medium text-slate-500 ml-1">ms</span>
              </div>
            </div>
            <div className="flex justify-between items-center pt-2 border-t border-slate-850">
              <span className="text-xs text-slate-500">Average Latency</span>
              <span className="text-sm font-semibold font-mono text-slate-300">
                {metrics ? `${metrics.avg_latency_ms.toFixed(2)}` : '0.00'} ms
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Cache Health */}
        <div className="relative group overflow-hidden bg-slate-900/40 border border-slate-900 rounded-2xl p-6 backdrop-blur">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <HardDrive className="w-24 h-24 text-emerald-400" />
          </div>
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-xl bg-emerald-950/60 border border-emerald-500/20 text-emerald-400">
              <HardDrive className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">Distributed Cache</h3>
          </div>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-slate-500 font-sans uppercase">Cache Hit Rate</div>
              <div className="text-4xl font-extrabold font-mono text-emerald-400 mt-1">
                {metrics ? `${metrics.cache_hit_rate.toFixed(1)}` : '0.0'}<span className="text-lg font-sans font-medium text-slate-500 ml-1">%</span>
              </div>
            </div>
            
            {/* Visual hit rate progress bar */}
            <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-850">
              <div 
                className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full transition-all duration-500" 
                style={{ width: `${metrics ? Math.min(100, Math.max(0, metrics.cache_hit_rate)) : 0}%` }}
              ></div>
            </div>

            <div className="flex justify-between items-center text-xs pt-1">
              <span className="text-slate-500">Hits: <strong className="text-slate-300">{metrics?.cache_hits || 0}</strong></span>
              <span className="text-slate-500">Misses: <strong className="text-slate-300">{metrics?.cache_misses || 0}</strong></span>
            </div>
          </div>
        </div>

        {/* Card 3: Batch Writes */}
        <div className="relative group overflow-hidden bg-slate-900/40 border border-slate-900 rounded-2xl p-6 backdrop-blur">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Database className="w-24 h-24 text-purple-400" />
          </div>
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-xl bg-purple-950/60 border border-purple-500/20 text-purple-400">
              <Database className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">Batch Write Reducer</h3>
          </div>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-slate-500 font-sans uppercase">DB Writes Saved</div>
              <div className="text-4xl font-extrabold font-mono text-purple-400 mt-1">
                {metrics ? `${metrics.db_writes_saved.toLocaleString()}` : '0'}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-850 text-xs text-slate-500">
              <div>
                Queue Buffer: <strong className="text-slate-300 font-mono">{metrics?.queue_size || 0} / 100</strong>
              </div>
              <div className="text-right">
                Flush Operations: <strong className="text-slate-300 font-mono">{metrics?.batch_flushes || 0}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Details Row: Live Rankings & Consistent Hashing Ring Console */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Section A: Live Rankings */}
        <div className="bg-slate-900/40 border border-slate-900 rounded-2xl p-6 backdrop-blur flex flex-col">
          <div className="flex items-center gap-2 mb-4 border-b border-slate-850 pb-3">
            <Activity className="w-5 h-5 text-brand-400" />
            <h3 className="text-md font-bold text-white uppercase tracking-wider">Live Trending Rankings</h3>
          </div>
          
          <div className="flex-grow overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300 font-sans">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500 text-xs font-semibold uppercase">
                  <th className="py-2.5">Rank</th>
                  <th className="py-2.5">Query</th>
                  <th className="py-2.5 text-right">Search Count</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850">
                {rankingTable.length > 0 ? (
                  rankingTable.slice(0, 10).map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                      <td className="py-3 font-mono font-bold text-slate-500">#{idx + 1}</td>
                      <td className="py-3 font-semibold text-white">{item.query}</td>
                      <td className="py-3 text-right font-mono text-brand-300 font-semibold">
                        {item.count.toLocaleString()}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={3} className="py-6 text-center text-slate-500">
                      No search rankings available. Seeds/Searches needed.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section B: Consistent Hashing Console */}
        <div className="bg-slate-900/40 border border-slate-900 rounded-2xl p-6 backdrop-blur flex flex-col h-[400px]">
          <div className="flex items-center justify-between mb-4 border-b border-slate-850 pb-3">
            <div className="flex items-center gap-2">
              <Server className="w-5 h-5 text-purple-400" />
              <h3 className="text-md font-bold text-white uppercase tracking-wider">Routing & Caching Logs</h3>
            </div>
            {routingLogs.length > 0 && (
              <button 
                onClick={onClearLogs}
                className="text-[10px] uppercase font-bold text-slate-500 hover:text-slate-300 border border-slate-800 px-2 py-0.5 rounded-md hover:bg-slate-900"
              >
                Clear Logs
              </button>
            )}
          </div>

          <div className="flex-grow bg-slate-950 border border-slate-850 rounded-xl p-4 font-mono text-xs overflow-y-auto no-scrollbar space-y-2 text-slate-400 shadow-inner flex flex-col-reverse">
            <div>
              {routingLogs.length > 0 ? (
                // Show logs from newest to oldest inside scrollbox
                [...routingLogs].reverse().map((log, idx) => {
                  let badgeColor = 'text-slate-400 border-slate-800 bg-slate-900';
                  if (log.includes('HIT')) badgeColor = 'text-emerald-400 border-emerald-950 bg-emerald-950/20';
                  else if (log.includes('MISS')) badgeColor = 'text-amber-400 border-amber-950 bg-amber-950/20';
                  else if (log.includes('Submitting')) badgeColor = 'text-purple-400 border-purple-950 bg-purple-950/20';
                  
                  return (
                    <div 
                      key={idx} 
                      className={`px-3 py-2 border rounded-lg mb-2 text-[11px] leading-relaxed transition-all ${badgeColor}`}
                    >
                      <span className="text-[10px] text-slate-500 mr-2">[{new Date().toLocaleTimeString()}]</span>
                      {log}
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-20 text-slate-600 italic">
                  No query logs captured. Start typing in the search box above to see real-time hashing and routing logic...
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
