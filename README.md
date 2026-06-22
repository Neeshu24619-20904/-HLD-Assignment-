# Search Typeahead System

A production-style Search Typeahead/Autocomplete System featuring:
- **React Frontend**: Built using Vite, TypeScript, and Tailwind CSS. Offers a modern search bar, autocomplete suggestion dropdown, keyboard navigation, and a live Developer Telemetry Dashboard.
- **FastAPI Backend**: Serving endpoints with low latency, incorporating latency metric calculations (p95 and average).
- **PostgreSQL Database**: Indexed for character prefix queries and historic telemetry updates.
- **Distributed Redis Cache Layer**: Routes prefixes across three logical caches (`cache-node-1`, `cache-node-2`, `cache-node-3`) using a custom **Consistent Hashing Ring** with virtual node replication.
- **Trie Service**: Implements prefix-based autocomplete lookup in $O(\text{prefix length})$ time using precomputed suggestion caches.
- **Batch Write Queue**: Buffers database writes to protect PostgreSQL from I/O load, merging and bulk upserting search submissions periodically.
- **Trending Scoring**: Calculated using an exponential time-decay formula combining search popularity with search event recency.

---

## 1. Quick Start (Docker Compose)

The entire application stack (PostgreSQL, 3 Redis Cache containers, FastAPI Backend, and React Frontend) can be initialized with one command:

```bash
docker compose up --build
```

### Accessing the Stack
- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **FastAPI API Server**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Seeding the 100,000+ Query Dataset
Once the containers are running and database tables are initialized, run the seed script to generate and load the 100,000+ query corpus:

```bash
docker compose exec backend python scripts/load_dataset.py
```
This script:
1. Dynamically generates a Zipfian-distributed search query dataset if `dataset/queries.csv` doesn't exist.
2. Bulk upserts the queries in high-speed database transaction batches.
3. Inserts initial historical search event logs for trending calculations.
4. Triggers the backend Trie to load.

---

## 2. API Documentation

### 1. Autocomplete Suggestions API
Returns up to 10 suggestions starting with the prefix, sorted by trending ranking score. Handles empty cases, mixed case, and special characters.

* **URL**: `/api/suggest`
* **Method**: `GET`
* **Query Params**: `q=<prefix>`
* **Response (HTTP 200)**:
  ```json
  {
    "suggestions": [
      { "query": "iphone 15 pro", "count": 85000 },
      { "query": "iphone charger", "count": 60000 }
    ]
  }
  ```

### 2. Search Submission API
Submits a query to the search system. Increments the query's search count (creates a new query entry if non-existent). To protect Postgres, writes are buffered in-memory and flushed in batches.

* **URL**: `/api/search`
* **Method**: `POST`
* **Payload**:
  ```json
  { "query": "iphone case" }
  ```
* **Response (HTTP 200)**:
  ```json
  { "message": "Searched" }
  ```

### 3. Global Trending API
Fetches the top 10 global trending queries calculated using recent search events with a decay factor.

* **URL**: `/api/trending`
* **Method**: `GET`
* **Response (HTTP 200)**:
  ```json
  {
    "trending": [
      { "query": "react tailwind", "count": 150 },
      { "query": "iphone 15 pro", "count": 220 }
    ]
  }
  ```

### 4. Cache Routing Debug API
Used to inspect which Redis cache node owns the prefix hash on the consistent hashing ring, and if it's currently cached (HIT/MISS).

* **URL**: `/api/cache/debug`
* **Method**: `GET`
* **Query Params**: `prefix=<prefix>`
* **Response (HTTP 200)**:
  ```json
  {
    "prefix": "iph",
    "cache_node": "cache-node-2",
    "cache_hit": true
  }
  ```

### 5. Telemetry Metrics API
Exposes average and p95 latencies, cache hit/miss count, cache hit rate (%), database writes saved, and current buffer size for dashboard analytics consumption.

* **URL**: `/api/metrics`
* **Method**: `GET`
* **Response (HTTP 200)**:
  ```json
  {
    "db_writes_saved": 87,
    "batch_flushes": 12,
    "queue_size": 0,
    "cache_hits": 142,
    "cache_misses": 53,
    "cache_hit_rate": 72.82,
    "avg_latency_ms": 0.42,
    "p95_latency_ms": 1.15
  }
  ```

---

## 3. Developer & Admin Dashboard

The application embeds an **Admin Analytics Dashboard** at `/admin` (accessible via the navigation header in the top-right):
1. **Performance Telemetry**: Gauges tracking p95 latency and average latency of auto-complete recommendations.
2. **Cache hit counters**: Live chart displaying cache hit rate % and total count of requests routed.
3. **Database Write Savings**: Demonstrates batching efficiency by showing total DB writes avoided.
4. **Consistent Hashing Terminal**: Logs the query prefixes and shows how the Consistent Hashing Ring routes key ownership clockwise (e.g. `Prefix "pyt" routed to [cache-node-1]`).
5. **Live Trending Rankings**: Real-time ranking of top queries based on time-decay decay algorithms.

---

## 4. Manual/Local Dev Setup (No Docker)

If you prefer to run the system natively outside Docker on your host machine:

### Backend
1. **Requirements**: Python 3.12, PostgreSQL server, and Redis server running locally.
2. Configure settings inside `backend/.env` (connection URLs default to localhost).
3. Install dependencies and start server:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
4. Seed database in a separate terminal:
   ```bash
   cd backend
   python scripts/load_dataset.py
   ```

### Frontend
1. **Requirements**: Node.js (v18+) and npm installed.
2. Install modules and start the development server:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Open [http://localhost:5173](http://localhost:5173) in your browser.
