import time
import logging
import threading
import sqlalchemy
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.search import SearchQuery, SearchEvent
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

class BatchSearchWriter:
    def __init__(self):
        self.buffer: List[Tuple[str, datetime]] = []
        self.lock = threading.Lock()
        self.last_flush_time = time.time()
        
        # Metrics
        self.total_searches_received = 0
        self.batch_flushes = 0
        self.db_writes_saved = 0
        
        # Background worker state
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None

    def add_search(self, query: str):
        """Adds a search query to the buffer. Triggers immediate flush if queue > 100."""
        if not query or not query.strip():
            return
            
        clean_query = query.strip()
        now = datetime.now(timezone.utc)
        
        flush_needed = False
        with self.lock:
            self.buffer.append((clean_query, now))
            self.total_searches_received += 1
            
            # Flush if buffer exceeds limit (100)
            if len(self.buffer) >= 100:
                flush_needed = True
                
        if flush_needed:
            logger.info("Buffer limit (100) reached. Triggering immediate database flush.")
            # Run flush in a separate thread to not block the API client
            threading.Thread(target=self.flush).start()

    def start_worker(self):
        """Starts the background flushing thread."""
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Batch writer background worker thread started.")

    def stop_worker(self):
        """Stops the background flushing thread and does a final flush."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        self.flush()  # Final flush
        logger.info("Batch writer background worker thread stopped.")

    def _worker_loop(self):
        """Periodically flushes the buffer every 30 seconds."""
        while self.running:
            time.sleep(1)
            time_since_last_flush = time.time() - self.last_flush_time
            if time_since_last_flush >= 30.0:
                with self.lock:
                    has_data = len(self.buffer) > 0
                if has_data:
                    logger.info("Time limit (30s) reached. Triggering periodic database flush.")
                    self.flush()
                else:
                    self.last_flush_time = time.time()

    def flush(self):
        """Flushes the buffer to the database by aggregating increments and invalidating caches."""
        # Retrieve buffer contents under lock
        with self.lock:
            if not self.buffer:
                self.last_flush_time = time.time()
                return
            current_batch = self.buffer
            self.buffer = []
            self.last_flush_time = time.time()

        # Process the batch
        # 1. Aggregate query count increments
        aggregates: Dict[str, int] = {}
        events_to_insert: List[SearchEvent] = []
        
        for query, timestamp in current_batch:
            aggregates[query] = aggregates.get(query, 0) + 1
            events_to_insert.append(SearchEvent(query=query, timestamp=timestamp))

        # 2. Database transaction
        db: Session = SessionLocal()
        try:
            # A. Bulk Upsert queries
            for query, count in aggregates.items():
                # Raw SQL bulk upsert to be fast and handle postgres conflicts cleanly
                # We update total_count and updated_at
                stmt = """
                    INSERT INTO search_queries (query, total_count, created_at, updated_at)
                    VALUES (:query, :count, NOW(), NOW())
                    ON CONFLICT (query) DO UPDATE
                    SET total_count = search_queries.total_count + EXCLUDED.total_count,
                        updated_at = EXCLUDED.updated_at;
                """
                db.execute(
                    sqlalchemy.text(stmt),
                    {"query": query, "count": count}
                )
            
            # B. Bulk insert events
            db.bulk_save_objects(events_to_insert)
            db.commit()
            
            # C. Invalidate cache for all prefixes of the updated queries
            for query in aggregates.keys():
                cache_service.invalidate_query_prefixes(query)
                
            # D. Update Metrics
            self.batch_flushes += 1
            # Writes saved = total entries in batch - number of database update operations (unique queries + 1 for bulk insert events)
            # Or as standard definition: writes saved = total search logs in batch - 1 flush transaction.
            # Let's count writes saved as total entries in batch - 1 (since we did it in one bulk session).
            # This matches standard batch writes saving logic.
            self.db_writes_saved += (len(current_batch) - 1)
            
            logger.info(f"Successfully flushed {len(current_batch)} search submissions to database. "
                        f"Database writes saved this batch: {len(current_batch) - 1}. "
                        f"Total saved: {self.db_writes_saved}.")
            
            # Trigger Trie reload asynchronously after DB changes
            from app.services.trending import trigger_trie_reload
            trigger_trie_reload()

        except Exception as e:
            db.rollback()
            logger.error(f"Error flushing search submissions batch to database: {e}")
            # Put items back in buffer in case of failure
            with self.lock:
                self.buffer.extend(current_batch)
        finally:
            db.close()

    def get_metrics(self) -> Dict[str, Any]:
        """Returns batch writer metrics."""
        return {
            "queue_size": len(self.buffer),
            "batch_flushes": self.batch_flushes,
            "db_writes_saved": self.db_writes_saved,
            "total_searches_received": self.total_searches_received
        }

# Global batch writer instance
batch_writer = BatchSearchWriter()
