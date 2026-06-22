import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import router
from app.services.batch_writer import batch_writer
from app.services.trending import trending_scheduler, recalculate_trending_scores

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events manager for FastAPI startup and shutdown."""
    logger.info("Initializing search typeahead system backend...")
    
    # 1. Initialize Postgres Tables
    try:
        init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        
    # 2. Recalculate trending scores and populate Trie on startup
    try:
        recalculate_trending_scores()
        logger.info("Initial Trie loading completed successfully.")
    except Exception as e:
        logger.error(f"Initial Trie loading failed: {e}")

    # 3. Start batch writing worker background thread
    batch_writer.start_worker()
    
    # 4. Start trending recalculation scheduler
    trending_scheduler.start()
    
    logger.info("Backend services started successfully.")
    
    yield
    
    logger.info("Stopping backend services...")
    # 5. Shut down workers and flush queues
    trending_scheduler.stop()
    batch_writer.stop_worker()
    logger.info("Backend services stopped successfully.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# Set up CORS middleware to allow calls from the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router under /api
app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Search Typeahead API. Access docs at /docs"}
