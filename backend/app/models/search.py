from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Index, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class SearchQuery(Base):
    __tablename__ = "search_queries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=1, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)

    __table_args__ = (
        # Index query with varchar_pattern_ops to optimize prefix searches (LIKE 'prefix%') in Postgres
        # We can also add it via migration, but we can specify it here if compiling specifically for Postgres.
        # Index("idx_queries_query_pattern", query, postgresql_ops={"query": "varchar_pattern_ops"}),
    )

class SearchEvent(Base):
    __tablename__ = "search_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
