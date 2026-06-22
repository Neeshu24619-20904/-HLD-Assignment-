import os
import csv
import random
import sys
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add /app to path so we can import app modules (WORKDIR inside Docker is /app)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, init_db
from app.models.search import SearchQuery, SearchEvent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("load_dataset")

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset")
DATASET_PATH = os.path.join(DATASET_DIR, "queries.csv")

# Word banks for generating search queries
nouns = ["iphone", "laptop", "python", "coffee", "shoes", "macbook", "react", "docker", "redis", "postgres", 
         "javascript", "headphones", "keyboard", "monitor", "course", "tutorial", "flight", "weather", 
         "recipe", "game", "book", "chair", "desk", "water bottle", "backpack", "shoes", "jacket", "shirt",
         "pizza", "burger", "camera", "phone case", "charger", "car", "housing", "rent", "job", "news"]

adjectives = ["best", "cheap", "top", "free", "latest", "easy", "online", "advanced", "complete", "new", 
              "wireless", "smart", "ergonomic", "portable", "waterproof", "mechanical", "gaming", "local"]

suffixes = ["for beginners", "tutorial", "review", "price", "guide", "download", "online", "near me", 
            "under 100", "2026", "alternatives", "vs code", "setup", "documentation", "tips", "tricks"]

def generate_queries(count=105000) -> list:
    """Generates a list of realistic search queries."""
    logger.info(f"Generating {count} unique queries...")
    queries = set()
    
    # Pre-add some standard queries to ensure high quality prefix matching
    high_quality_bases = [
        "iphone", "iphone 15", "iphone 15 pro", "iphone case", "iphone charger", 
        "iphone 15 case", "iphone screensaver", "iphone 14", "iphone 13", "iphone se",
        "java", "java tutorial", "java download", "java jdk", "java compiler", "java programming",
        "python", "python tutorial", "python download", "python documentation", "python variables",
        "react", "react native", "react js", "react hooks", "react router", "react tailwind"
    ]
    for q in high_quality_bases:
        queries.add(q)
        
    # Max combinations is around 39 * 18 * 16 = 11,232. To generate 105,000 unique queries, we must allow dynamic suffixes or fallback digits.
    attempts = 0
    while len(queries) < count:
        pattern = random.randint(1, 4)
        if pattern == 1:
            q = f"{random.choice(adjectives)} {random.choice(nouns)}"
        elif pattern == 2:
            q = f"{random.choice(nouns)} {random.choice(suffixes)}"
        elif pattern == 3:
            q = f"{random.choice(adjectives)} {random.choice(nouns)} {random.choice(suffixes)}"
        else:
            q = f"{random.choice(nouns)}"
            
        q = q.lower()
        if q in queries:
            attempts += 1
            # If we keep getting duplicates, append a random number/counter to ensure uniqueness
            if attempts > 10000:
                q = f"{q} {random.randint(10, 9999)}"
        else:
            attempts = 0
            
        queries.add(q)
        
    # Sort and rank to assign counts using Zipf's Law (power law distribution)
    # count(rank) = C / rank^alpha (alpha ~ 0.85)
    # This matches realistic search query distributions
    sorted_queries = sorted(list(queries))
    random.shuffle(sorted_queries) # randomize matching query text to rank
    
    logger.info("Applying Zipfian distribution to query counts...")
    queries_with_counts = []
    C = 1200000.0  # Constant factor
    alpha = 0.85
    
    for rank, query in enumerate(sorted_queries, 1):
        count_val = int(C / (rank ** alpha))
        # Ensure count is at least 1
        count_val = max(1, count_val)
        queries_with_counts.append((query, count_val))
        
    # Sort by count descending
    queries_with_counts.sort(key=lambda x: -x[1])
    return queries_with_counts

def create_dataset_if_not_exists():
    """Generates the CSV file if it does not exist already."""
    if not os.path.exists(DATASET_DIR):
        os.makedirs(DATASET_DIR)
        
    if os.path.exists(DATASET_PATH):
        logger.info(f"Dataset already exists at {DATASET_PATH}. Skipping generation.")
        return

    queries_data = generate_queries(105000)
    
    logger.info(f"Writing dataset to CSV at {DATASET_PATH}...")
    with open(DATASET_PATH, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["query", "count"])
        for q, c in queries_data:
            writer.writerow([q, c])
            
    logger.info(f"Dataset CSV created successfully. Total rows: {len(queries_data)}")

def load_data_to_postgres():
    """Loads the queries CSV data into the PostgreSQL database."""
    logger.info("Connecting to PostgreSQL database...")
    db: Session = SessionLocal()
    
    try:
        # Clear existing tables first for a clean seed
        logger.info("Cleaning existing database tables...")
        db.execute(text("TRUNCATE TABLE search_events RESTART IDENTITY CASCADE;"))
        db.execute(text("TRUNCATE TABLE search_queries RESTART IDENTITY CASCADE;"))
        db.commit()
        
        logger.info(f"Reading queries from CSV file: {DATASET_PATH}")
        queries_to_load = []
        with open(DATASET_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader) # skip header
            for row in reader:
                if len(row) == 2:
                    queries_to_load.append({"query": row[0], "total_count": int(row[1])})

        total_queries = len(queries_to_load)
        logger.info(f"Parsed {total_queries} queries from CSV. Starting seed...")
        
        # Insert in batches of 5000 using raw execute to be extremely fast
        batch_size = 5000
        stmt = text("""
            INSERT INTO search_queries (query, total_count, created_at, updated_at)
            VALUES (:query, :total_count, NOW(), NOW())
        """)
        
        for idx in range(0, total_queries, batch_size):
            batch = queries_to_load[idx:idx+batch_size]
            db.execute(stmt, batch)
            db.commit()
            if (idx + batch_size) % 20000 == 0 or (idx + batch_size) >= total_queries:
                logger.info(f"Seeded {min(idx + batch_size, total_queries)} / {total_queries} queries.")
                
        logger.info("Successfully seeded search_queries table.")

        # Seed some recent SearchEvents for trending computation (e.g. last 7 days)
        logger.info("Generating and seeding historical search events for trending calculations...")
        popular_searches = [
            "iphone 15 pro", "react tailwind", "python tutorial", 
            "docker setup", "redis cache", "postgres copy", 
            "javascript hooks", "java compiler", "weather near me"
        ]
        
        events_to_seed = []
        now = datetime.now(timezone.utc)
        
        for q in popular_searches:
            # Generate random number of search events
            # Give some queries high frequency in the last 1 hour to make them highly trending!
            # e.g. "react tailwind" gets 150 searches in last hour
            # "iphone 15 pro" gets 200 searches in last 24h
            if q == "react tailwind":
                count_events = 150
                times = [now - timedelta(minutes=random.randint(1, 55)) for _ in range(count_events)]
            elif q == "iphone 15 pro":
                count_events = 220
                times = [now - timedelta(hours=random.randint(1, 23)) for _ in range(count_events)]
            else:
                count_events = random.randint(30, 80)
                times = [now - timedelta(days=random.randint(0, 6)) for _ in range(count_events)]
                
            for t in times:
                events_to_seed.append({"query": q, "timestamp": t})
                
        # Bulk save events
        event_stmt = text("""
            INSERT INTO search_events (query, timestamp)
            VALUES (:query, :timestamp)
        """)
        db.execute(event_stmt, events_to_seed)
        db.commit()
        logger.info(f"Seeded {len(events_to_seed)} historical search events successfully.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Seeding failed: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting dataset setup process...")
    # Make sure tables exist
    init_db()
    create_dataset_if_not_exists()
    load_data_to_postgres()
    logger.info("Dataset setup completed successfully!")
