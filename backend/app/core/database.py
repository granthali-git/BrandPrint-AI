"""SQLAlchemy database engine and session configuration for Supabase / PostgreSQL."""
from typing import Generator, AsyncGenerator
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# Normalize PostgreSQL URL for SQLAlchemy
# Supabase provides URLs starting with 'postgres://' or 'postgresql://'
def get_sync_database_url(url: str) -> str:
    """Ensure URL uses postgresql+psycopg2 driver for sync operations."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def get_async_database_url(url: str) -> str:
    """Ensure URL uses postgresql+asyncpg driver for async operations."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return url


SYNC_DATABASE_URL = get_sync_database_url(settings.SUPABASE_DB_URL)
ASYNC_DATABASE_URL = get_async_database_url(settings.SUPABASE_DB_URL)

# Configure Sync Engine (for standard FastAPI endpoints and migrations)
# pool_pre_ping=True is essential for Supabase connection timeouts
sync_engine_args = {
    "pool_pre_ping": True,
}
if "sqlite" not in SYNC_DATABASE_URL:
    sync_engine_args.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,
    })

engine = create_engine(SYNC_DATABASE_URL, **sync_engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Configure Async Engine (for high-throughput async pipelines and LLM streaming)
async_engine = None
AsyncSessionLocal = None
try:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    async_engine_args = {
        "pool_pre_ping": True,
    }
    if "sqlite" not in ASYNC_DATABASE_URL:
        async_engine_args.update({
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 1800,
        })
    async_engine = create_async_engine(ASYNC_DATABASE_URL, **async_engine_args)
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
except Exception as e:
    logger.info(f"Async engine not initialized (requires greenlet/asyncpg): {e}")


# Declarative Base for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a synchronous database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator["AsyncSession", None]:
    """Dependency that yields an asynchronous database session."""
    if AsyncSessionLocal is None:
        raise RuntimeError("AsyncSessionLocal is not configured. Check database driver.")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
