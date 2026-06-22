const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export interface SuggestionItem {
  query: string;
  count: number;
}

export interface SuggestionResponse {
  suggestions: SuggestionItem[];
}

export interface SearchResponse {
  message: string;
}

export interface TrendingResponse {
  trending: SuggestionItem[];
}

export interface CacheDebugResponse {
  prefix: string;
  cache_node: string;
  cache_hit: boolean;
}

export interface MetricsResponse {
  db_writes_saved: number;
  batch_flushes: number;
  queue_size: number;
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
}

export const fetchSuggestions = async (prefix: string): Promise<SuggestionResponse> => {
  const res = await fetch(`${BASE_URL}/api/suggest?q=${encodeURIComponent(prefix)}`);
  if (!res.ok) throw new Error('Failed to fetch suggestions');
  return res.json();
};

export const submitSearch = async (query: string): Promise<SearchResponse> => {
  const res = await fetch(`${BASE_URL}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error('Failed to record search');
  return res.json();
};

export const fetchTrending = async (): Promise<TrendingResponse> => {
  const res = await fetch(`${BASE_URL}/api/trending`);
  if (!res.ok) throw new Error('Failed to fetch trending searches');
  return res.json();
};

export const debugCache = async (prefix: string): Promise<CacheDebugResponse> => {
  const res = await fetch(`${BASE_URL}/api/cache/debug?prefix=${encodeURIComponent(prefix)}`);
  if (!res.ok) throw new Error('Failed to debug cache');
  return res.json();
};

export const fetchMetrics = async (): Promise<MetricsResponse> => {
  const res = await fetch(`${BASE_URL}/api/metrics`);
  if (!res.ok) throw new Error('Failed to fetch metrics');
  return res.json();
};
