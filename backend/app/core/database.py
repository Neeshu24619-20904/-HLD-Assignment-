from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from app.core.config import settings
from app.models.search import Base

engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping is useful to automatically reconnect when postgres restarts (e.g. in Docker Compose)
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    """Dependency for API endpoints to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """Initializes tables in the database."""
    # This creates all tables if they don't exist yet (fallback for alembic)
    Base.metadata.create_all(bind=engine)
