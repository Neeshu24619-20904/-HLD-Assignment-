from pydantic import BaseModel
from typing import List

class SuggestionItem(BaseModel):
    query: str
    count: int

class SuggestionResponse(BaseModel):
    suggestions: List[SuggestionItem]

class SearchRequest(BaseModel):
    query: str

class SearchResponse(BaseModel):
    message: str

class TrendingResponse(BaseModel):
    trending: List[SuggestionItem]

class CacheDebugResponse(BaseModel):
    prefix: str
    cache_node: str
    cache_hit: bool

class MetricsResponse(BaseModel):
    # Batch writer metrics
    db_writes_saved: int
    batch_flushes: int
    queue_size: int
    
    # Cache metrics
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    
    # Performance metrics
    avg_latency_ms: float
    p95_latency_ms: float
