import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.trie import trie_service

logger = logging.getLogger(__name__)

# Global flag and condition to rate-limit Trie reloads
_reload_pending = False
_reload_lock = threading.Lock()

def trigger_trie_reload():
    """
    Triggers an asynchronous reload of the Trie. 
    Limits execution frequency to prevent CPU thrashing.
    """
    global _reload_pending
    with _reload_lock:
        if _reload_pending:
            return
        _reload_pending = True
    
    # Run the reload in a background thread
    threading.Thread(target=_reload_worker).start()

def _reload_worker():
    global _reload_pending
    # Small sleep to batch consecutive write triggers
    time.sleep(1.0)
    try:
        recalculate_trending_scores()
    except Exception as e:
        logger.error(f"Error in background Trie reload: {e}")
    finally:
        with _reload_lock:
            _reload_pending = False

def recalculate_trending_scores():
    """
    Recalculates the recency-aware trending score for all queries
    and reloads the Trie with the new scores.
    Formula:
        score = 0.7 * normalized_total_count + 0.3 * recent_activity_score
    """
    logger.info("Recalculating trending scores...")
    db: Session = SessionLocal()
    try:
        # 1. Fetch maximum total_count for normalization
        max_count_res = db.execute(text("SELECT MAX(total_count) FROM search_queries")).scalar()
        max_total_count = float(max_count_res) if max_count_res else 1.0

        # 2. Fetch search event activity from last hour, day, week
        # We group counts per query in these timeframes
        event_query = """
            SELECT 
                query,
                COUNT(CASE WHEN timestamp >= NOW() - INTERVAL '1 hour' THEN 1 END) as count_1h,
                COUNT(CASE WHEN timestamp >= NOW() - INTERVAL '1 day' AND timestamp < NOW() - INTERVAL '1 hour' THEN 1 END) as count_24h,
                COUNT(CASE WHEN timestamp >= NOW() - INTERVAL '7 days' AND timestamp < NOW() - INTERVAL '1 day' THEN 1 END) as count_7d
            FROM search_events
            WHERE timestamp >= NOW() - INTERVAL '7 days'
            GROUP BY query
        """
        event_res = db.execute(text(event_query)).fetchall()
        
        # Calculate recent activity score for each query:
        # weight: 1.0 for last hour, 0.5 for last 24h, 0.1 for last 7d
        recent_scores: Dict[str, float] = {}
        for row in event_res:
            q = row[0]
            c_1h = float(row[1] or 0)
            c_24h = float(row[2] or 0)
            c_7d = float(row[3] or 0)
            score = (c_1h * 1.0) + (c_24h * 0.5) + (c_7d * 0.1)
            recent_scores[q] = score

        max_recent_score = max(recent_scores.values()) if recent_scores else 1.0
        if max_recent_score == 0:
            max_recent_score = 1.0

        # 3. Fetch all queries to load into Trie
        queries_res = db.execute(text("SELECT query, total_count FROM search_queries")).fetchall()
        
        items_to_load: List[Dict[str, Any]] = []
        for row in queries_res:
            query = row[0]
            total_count = row[1]
            
            # Normalize total count (0.0 to 1.0)
            norm_total = float(total_count) / max_total_count
            
            # Get and normalize recent activity score (0.0 to 1.0)
            raw_recent = recent_scores.get(query, 0.0)
            norm_recent = raw_recent / max_recent_score
            
            # Recency-aware score formula
            score = (0.7 * norm_total) + (0.3 * norm_recent)
            
            items_to_load.append({
                "query": query,
                "count": total_count,
                "score": score
            })

        # 4. Reload Trie Service
        trie_service.reload(items_to_load)
        logger.info("Trending scores recalculated successfully.")

    except Exception as e:
        logger.error(f"Error recalculating trending scores: {e}")
    finally:
        db.close()

class TrendingScheduler:
    """Background service to trigger trending recalculations every minute."""
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Trending scheduler background thread started.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Trending scheduler background thread stopped.")

    def _run_loop(self):
        while self.running:
            # Sleep 60 seconds
            time.sleep(settings.TRENDING_RECALC_INTERVAL)
            if self.running:
                try:
                    recalculate_trending_scores()
                except Exception as e:
                    logger.error(f"Error in scheduler trending run: {e}")

# Global scheduler instance
trending_scheduler = TrendingScheduler()
