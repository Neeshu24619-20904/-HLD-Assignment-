import json
import logging
import redis
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.services.consistent_hash import ConsistentHashRing

logger = logging.getLogger(__name__)

class MemoryCacheFallback:
    """Mock Redis client for local development if Redis is unavailable."""
    def __init__(self):
        self.store: Dict[str, str] = {}
        self.ttls: Dict[str, float] = {}

    def get(self, key: str) -> Optional[str]:
        return self.store.get(key)

    def setex(self, key: str, time: int, value: str):
        self.store[key] = value

    def delete(self, key: str):
        self.store.pop(key, None)

    def flushall(self):
        self.store.clear()

class CacheService:
    def __init__(self):
        # Stats tracking for Admin/Developer Dashboard
        self.hits = 0
        self.misses = 0
        
        # Configure the logical nodes on the consistent hash ring
        # Physical nodes: 'cache-node-1', 'cache-node-2', 'cache-node-3'
        self.nodes = ["cache-node-1", "cache-node-2", "cache-node-3"]
        self.ring = ConsistentHashRing(nodes=self.nodes, replicas=50)
        
        # Redis connection objects per node
        self.clients: Dict[str, Any] = {}
        
        parsed = settings.parsed_redis_nodes
        # Initialize Redis clients based on parsed configurations
        for i, node_name in enumerate(self.nodes):
            # Try to fetch corresponding URL from settings
            url = None
            if i < len(parsed):
                url = parsed[i]["url"]
            else:
                # Local fallback defaults if settings are short
                url = f"redis://localhost:6379/{i}"
                
            try:
                # Test connection immediately
                client = redis.Redis.from_url(url, socket_connect_timeout=2.0, decode_responses=True)
                client.ping()
                self.clients[node_name] = client
                logger.info(f"Successfully connected to Redis Node {node_name} at {url}")
            except Exception as e:
                logger.warning(f"Could not connect to Redis Node {node_name} at {url} ({e}). Falling back to memory cache.")
                self.clients[node_name] = MemoryCacheFallback()

    def get_node_for_key(self, key: str) -> str:
        """Determines which logical node owns the given key."""
        return self.ring.get_node(key) or "cache-node-1"

    def get_suggestions(self, prefix: str, mode: str = "pop") -> Optional[List[Dict[str, Any]]]:
        """
        Fetches suggestions for a prefix from the cache node owned by this prefix.
        :param prefix: The prefix search string.
        :param mode: Either 'pop' (popularity) or 'trend' (recency-decayed trending).
        """
        node_name = self.get_node_for_key(prefix)
        client = self.clients.get(node_name)
        
        cache_key = f"prefix:{mode}:{prefix.lower()}"
        try:
            cached_data = client.get(cache_key)
            if cached_data:
                self.hits += 1
                logger.debug(f"[Cache HIT] Node: {node_name}, Key: {cache_key}")
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error reading from Redis node {node_name}: {e}")
            
        self.misses += 1
        logger.debug(f"[Cache MISS] Node: {node_name}, Key: {cache_key}")
        return None

    def set_suggestions(self, prefix: str, suggestions: List[Dict[str, Any]], mode: str = "pop", ttl: int = 300):
        """
        Saves prefix suggestions to the appropriate cache node.
        """
        node_name = self.get_node_for_key(prefix)
        client = self.clients.get(node_name)
        
        cache_key = f"prefix:{mode}:{prefix.lower()}"
        try:
            client.setex(cache_key, ttl, json.dumps(suggestions))
            logger.debug(f"[Cache SET] Node: {node_name}, Key: {cache_key}, TTL: {ttl}s")
        except Exception as e:
            logger.error(f"Error writing to Redis node {node_name}: {e}")

    def invalidate_prefix(self, prefix: str):
        """
        Invalidates cached keys (both popularity and trending) for a prefix.
        """
        node_name = self.get_node_for_key(prefix)
        client = self.clients.get(node_name)
        
        try:
            client.delete(f"prefix:pop:{prefix.lower()}")
            client.delete(f"prefix:trend:{prefix.lower()}")
            logger.debug(f"[Cache INVALIDATE] Node: {node_name}, Prefix: {prefix}")
        except Exception as e:
            logger.error(f"Error invalidating cache on Redis node {node_name}: {e}")

    def invalidate_query_prefixes(self, query: str):
        """
        Given a full query (e.g. "iphone 15"), invalidates all of its prefix keys.
        """
        for i in range(1, len(query) + 1):
            prefix = query[:i]
            self.invalidate_prefix(prefix)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns cache metrics for dashboard consumption."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total
        }

# Global cache service instance
cache_service = CacheService()
