# 🔍 NexusSearch — Search Typeahead System

A production-grade **Search Autocomplete / Typeahead** system built as a High-Level Design (HLD) assignment. It demonstrates distributed systems concepts including a Trie-based prefix search engine, consistent hashing across a Redis cluster, batch write buffering, and recency-weighted trending scores.

---

## 🏗️ Architecture Overview

```
User Types "iph"
      │
      ▼
┌─────────────────┐
│  React Frontend  │  (Vite + TypeScript + Tailwind)
│  localhost:3000  │
└────────┬────────┘
         │ GET /api/suggest?q=iph
         ▼
┌─────────────────┐       ┌─────────────────────────────────┐
│  FastAPI Backend │──────▶│  Consistent Hash Ring           │
│  localhost:8000  │       │  ┌──────────┐ ┌──────────┐    │
└────────┬────────┘       │  │ Redis #1 │ │ Redis #2 │    │
         │                │  └──────────┘ └──────────┘    │
         │                │       ┌──────────┐             │
         │                │       │ Redis #3 │             │
         ▼                │       └──────────┘             │
┌─────────────────┐       └─────────────────────────────────┘
│  Trie Service   │
│  (In-Memory)    │
└────────┬────────┘
         │  (on miss)
         ▼
┌─────────────────┐
│   PostgreSQL    │
│  search_queries │
└─────────────────┘
```

### Key Components

| Component | Technology | Role |
|-----------|-----------|------|
| Frontend | React + Vite + TypeScript + Tailwind | Search UI, dashboard, cache routing display |
| Backend | FastAPI + Python 3.12 | REST API, orchestration |
| Trie Service | In-memory Python | O(prefix_len) autocomplete lookup |
| Cache Layer | Redis ×3 (Consistent Hashing) | Prefix result caching across 3 logical nodes |
| Database | PostgreSQL 16 | Persistent query store, search events |
| Batch Writer | Python threading | Buffers writes, reduces DB I/O pressure |
| Trending Engine | Background scheduler | Recency-weighted score recalculation every 60s |

---

## 🚀 Quick Start with Docker

> **Requirements:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### 1. Clone the repository

```bash
git clone https://github.com/Neeshu24619-20904/-HLD-Assignment-.git
cd "-HLD-Assignment-"
```

### 2. Start all services

```bash
docker compose up --build
```

This one command will:
- Build the **backend** and **frontend** Docker images
- Start **PostgreSQL**, **3 Redis nodes**, the **FastAPI backend**, and the **React frontend**
- Automatically **generate and seed 105,000 queries** into PostgreSQL
- Load all queries into the **Trie** and start the **trending scheduler**

> ⏳ **First run:** ~2–3 minutes (image downloads + DB seeding).  
> ⚡ **Subsequent runs:** ~30 seconds (images and DB already ready).

### 3. Open the app

| Service | URL |
|---------|-----|
| 🌐 Frontend (Search UI) | http://localhost:3000 |
| ⚡ Backend API | http://localhost:8000 |
| 📖 Swagger API Docs | http://localhost:8000/docs |

---

## ✅ What to Expect on Startup

Watch the logs with:
```bash
docker compose logs -f backend
```

You should see this sequence, confirming everything is healthy:

```
Generating 105000 unique queries...
Dataset CSV created successfully. Total rows: 105000
Seeded 20000 / 105000 queries.
Seeded 40000 / 105000 queries.
...
Seeded 105000 / 105000 queries.
Seeded 820 historical search events successfully.
Dataset setup completed successfully!
Trie successfully reloaded with 105000 queries.
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

---

## 🛑 Stopping & Resetting

| Action | Command |
|--------|---------|
| Stop all containers (keep data) | `docker compose down` |
| Stop and **wipe the database** (full reset) | `docker compose down -v` |
| Run in background (detached) | `docker compose up --build -d` |
| Rebuild only the backend | `docker compose up --build backend` |
| View live backend logs | `docker compose logs -f backend` |

---

## 📡 API Reference

### `GET /api/suggest?q=<prefix>`
Returns up to 10 prefix-matched autocomplete suggestions sorted by trending score.

```bash
# PowerShell
Invoke-RestMethod "http://localhost:8000/api/suggest?q=iphone"

# Response
{
  "suggestions": [
    { "query": "iphone 15 pro", "count": 144 },
    { "query": "iphone tutorial", "count": 5553 },
    ...
  ]
}
```

---

### `POST /api/search`
Submits a search query. Writes are batched in-memory and flushed to PostgreSQL every 30 seconds (or when buffer hits 100 entries).

```bash
# PowerShell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/search" `
  -ContentType "application/json" `
  -Body '{"query": "iphone 15 pro"}'

# Response
{ "message": "Searched" }
```

---

### `GET /api/trending`
Returns the top 10 globally trending queries, ranked by a recency-weighted score:
`score = 0.7 × normalized_total_count + 0.3 × recent_activity`

```bash
Invoke-RestMethod "http://localhost:8000/api/trending"

# Response
{
  "trending": [
    { "query": "react tailwind", "count": 661 },
    { "query": "iphone 15 pro",  "count": 144 },
    ...
  ]
}
```

---

### `GET /api/cache/debug?prefix=<prefix>`
Shows which Redis node owns the prefix key (via consistent hashing) and whether it is currently cached.

```bash
Invoke-RestMethod "http://localhost:8000/api/cache/debug?prefix=react"

# Response
{
  "prefix":     "react",
  "cache_node": "cache-node-3",
  "cache_hit":  true
}
```

---

### `GET /api/metrics`
Returns live telemetry: latency stats, cache hit/miss counts, and batch write savings.

```bash
Invoke-RestMethod "http://localhost:8000/api/metrics"

# Response
{
  "db_writes_saved":  87,
  "batch_flushes":    12,
  "queue_size":        0,
  "cache_hits":       142,
  "cache_misses":      53,
  "cache_hit_rate":  72.82,
  "avg_latency_ms":   0.42,
  "p95_latency_ms":   1.15
}
```

---

## 🧭 Frontend Features

### Search Tab
- **Live typeahead dropdown** — suggestions appear after 300ms debounce
- **Keyboard navigation** — `↑ ↓` to navigate, `Enter` to select, `Escape` to close
- **Consistent Hash indicator** — shows which Redis node owns the current prefix and cache HIT/MISS status in real time
- **Trending section** — clickable trending query tags at the bottom

### Dashboard Tab (Admin)
- **Latency gauges** — avg and p95 latency
- **Cache hit rate chart** — live hit/miss ratio
- **DB write savings** — demonstrates batch write efficiency
- **Consistent hash routing log** — shows prefix → node routing history
- **Live trending rankings** — top queries updated every minute

---

## ⚙️ How the System Works

### 1. Trie (Prefix Search)
- All 105,000 queries are loaded into an in-memory Trie at startup
- Each Trie node stores the **top 10 suggestions** passing through it (precomputed)
- Lookup is `O(prefix_length)` — no database query needed on a cache miss

### 2. Consistent Hashing (Redis Layer)
- A hash ring with **50 virtual nodes per physical node** maps prefix keys to one of 3 Redis containers
- Each prefix always routes to the same node — deterministic and load-balanced
- On Redis cache **miss**: Trie is queried → result is stored back into Redis (TTL 300s)

### 3. Batch Write Queue
- Every user search is pushed to an **in-memory buffer**
- Buffer is flushed to PostgreSQL every **30 seconds** or when it reaches **100 entries**
- Reduces N individual DB writes to 1 bulk upsert per flush cycle

### 4. Trending Score
- A background scheduler recalculates scores every **60 seconds**
- Formula: `score = 0.7 × norm_total_count + 0.3 × norm_recent_activity`
- Recent activity is weighted: last 1 hour (`×1.0`), last 24 hours (`×0.5`), last 7 days (`×0.1`)
- After recalculation, the Trie is atomically rebuilt with new scores

---

## 🗂️ Project Structure

```
HLD-Assignment/
├── docker-compose.yml          # Orchestrates all 6 containers
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             # FastAPI app + lifespan startup
│   │   ├── api/routes.py       # All API endpoints
│   │   ├── core/
│   │   │   ├── config.py       # Settings (env vars)
│   │   │   └── database.py     # SQLAlchemy engine + session
│   │   ├── models/search.py    # SearchQuery + SearchEvent ORM models
│   │   ├── schemas/search.py   # Pydantic request/response schemas
│   │   └── services/
│   │       ├── trie.py         # Trie data structure + TrieService
│   │       ├── cache_service.py# Redis consistent hash cache layer
│   │       ├── consistent_hash.py # Hash ring implementation
│   │       ├── trending.py     # Score recalculation + scheduler
│   │       └── batch_writer.py # Buffered write queue
│   └── scripts/
│       └── load_dataset.py     # Dataset generation + DB seed script
└── frontend/
    ├── Dockerfile
    └── src/
        ├── App.tsx
        ├── components/
        │   ├── SearchBox.tsx       # Main search input + dropdown
        │   ├── TrendingList.tsx    # Trending tags display
        │   └── AnalyticsDashboard.tsx # Admin metrics dashboard
        └── services/api.ts         # All fetch calls to the backend
```

---

## 🛠️ Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons |
| Backend | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 (×3 nodes) |
| Containerization | Docker, Docker Compose |
