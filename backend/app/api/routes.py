import time
import math
import collections
import threading
import logging
import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.search import (
    SuggestionResponse, SearchRequest, SearchResponse, 
    TrendingResponse, CacheDebugResponse, MetricsResponse
)
from app.services.trie import trie_service
from app.services.cache_service import cache_service
from app.services.batch_writer import batch_writer

logger = logging.getLogger(__name__)
router = APIRouter()

class LatencyTracker:
    """Thread-safe latency tracker using deque to compute moving average and p95."""
    def __init__(self, maxlen=1000):
        self.latencies = collections.deque(maxlen=maxlen)
        self.lock = threading.Lock()

    def record(self, duration_ms: float):
        with self.lock:
            self.latencies.append(duration_ms)

    def get_stats(self):
        with self.lock:
            if not self.latencies:
                return 0.0, 0.0
            sorted_lat = sorted(self.latencies)
            n = len(sorted_lat)
            avg = sum(sorted_lat) / n
            
            # Simple math percentile index (95th)
            p95_idx = int(math.ceil(n * 0.95)) - 1
            p95_idx = max(0, min(p95_idx, n - 1))
            p95 = sorted_lat[p95_idx]
            
            return avg, p95

latency_tracker = LatencyTracker()

@router.get("/suggest", response_model=SuggestionResponse)
def suggest(q: str = Query("", description="Search prefix"), db: Session = Depends(get_db)):
    """
    Returns up to 10 prefix-matched suggestions sorted by score.
    Attempts Cache check first, then falls back to Trie, then DB.
    """
    start_time = time.perf_counter()
    
    # Handle empty input
    if not q or not q.strip():
        duration_ms = (time.perf_counter() - start_time) * 1000
        latency_tracker.record(duration_ms)
        return {"suggestions": []}
        
    clean_prefix = q.strip().lower()
    
    # 1. Fetch suggestions from Cache
    cached = cache_service.get_suggestions(clean_prefix, mode="pop")
    if cached is not None:
        duration_ms = (time.perf_counter() - start_time) * 1000
        latency_tracker.record(duration_ms)
        return {"suggestions": cached}
        
    # 2. Cache Miss: Retrieve from Trie (which stores recency-decayed scores)
    trie_results = trie_service.search(clean_prefix)
    
    # 3. Fallback: If Trie is empty/not loaded yet, query database directly
    if not trie_results:
        stmt = """
            SELECT query, total_count FROM search_queries
            WHERE query LIKE :prefix
            ORDER BY total_count DESC
            LIMIT 10
        """
        try:
            db_res = db.execute(sqlalchemy.text(stmt), {"prefix": f"{clean_prefix}%"}).fetchall()
            trie_results = [{"query": row[0], "count": row[1]} for row in db_res]
        except Exception as e:
            logger.error(f"Error querying fallback DB suggestions: {e}")
            trie_results = []

    # Format output items
    suggestions = [{"query": item["query"], "count": item["count"]} for item in trie_results]
    
    # 4. Save back to cache node
    cache_service.set_suggestions(clean_prefix, suggestions, mode="pop", ttl=300)
    
    duration_ms = (time.perf_counter() - start_time) * 1000
    latency_tracker.record(duration_ms)
    
    return {"suggestions": suggestions}

@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest):
    """
    Registers a search submission. 
    Queries are pushed into the batch queue to reduce DB writes.
    """
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
    batch_writer.add_search(query)
    return {"message": "Searched"}

@router.get("/trending", response_model=TrendingResponse)
def trending():
    """Returns top 10 global trending queries calculated via recency weights."""
    trending_items = trie_service.get_trending()
    
    # Map to schema output
    formatted = [{"query": item["query"], "count": item["count"]} for item in trending_items[:10]]
    return {"trending": formatted}

@router.get("/cache/debug", response_model=CacheDebugResponse)
def cache_debug(prefix: str = Query(..., description="Query prefix to debug")):
    """
    Exposes which Redis cache node owns the key and if it's currently a hit.
    """
    clean_prefix = prefix.strip().lower()
    node_name = cache_service.get_node_for_key(clean_prefix)
    
    client = cache_service.clients.get(node_name)
    cache_key = f"prefix:pop:{clean_prefix}"
    has_key = False
    try:
        has_key = client.get(cache_key) is not None
    except Exception:
        pass
        
    return {
        "prefix": clean_prefix,
        "cache_node": node_name,
        "cache_hit": has_key
    }

@router.get("/metrics", response_model=MetricsResponse)
def get_metrics():
    """Aggregates and reports backend latency, cache hit/miss, and write batching metrics."""
    batch_m = batch_writer.get_metrics()
    cache_m = cache_service.get_metrics()
    avg_lat, p95_lat = latency_tracker.get_stats()
    
    return {
        "db_writes_saved": batch_m["db_writes_saved"],
        "batch_flushes": batch_m["batch_flushes"],
        "queue_size": batch_m["queue_size"],
        
        "cache_hits": cache_m["cache_hits" if "cache_hits" in cache_m else "hits"],
        "cache_misses": cache_m["cache_misses" if "cache_misses" in cache_m else "misses"],
        "cache_hit_rate": cache_m["cache_hit_rate" if "cache_hit_rate" in cache_m else "hit_rate"],
        
        "avg_latency_ms": round(avg_lat, 2),
        "p95_latency_ms": round(p95_lat, 2)
    }
