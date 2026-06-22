import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Search Typeahead System"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/typeahead"
    
    # Redis Nodes - comma-separated list of nodes
    # For Docker Compose, they will resolve to redis-node-1, redis-node-2, redis-node-3.
    # For local testing, we fallback to local Redis with DB 1, 2, and 3.
    REDIS_NODES: str = "redis-node-1=redis://redis-node-1:6381/1,redis-node-2=redis://redis-node-2:6382/2,redis-node-3=redis://redis-node-3:6383/3"
    
    # Batch writes configuration
    BATCH_FLUSH_INTERVAL: float = 30.0  # seconds
    BATCH_MAX_SIZE: int = 100
    
    # Trending calculation configuration
    TRENDING_RECALC_INTERVAL: float = 60.0  # seconds
    
    # Dataset Config
    DATASET_SIZE: int = 100000
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def parsed_redis_nodes(self) -> List[dict]:
        """
        Parses REDIS_NODES string like "node-1=redis://...,node-2=redis://..."
        into a list of dicts: [{"name": "node-1", "url": "redis://..."}]
        """
        nodes = []
        for pair in self.REDIS_NODES.split(","):
            if "=" in pair:
                name, url = pair.split("=", 1)
                nodes.append({"name": name.strip(), "url": url.strip()})
        return nodes

settings = Settings()
