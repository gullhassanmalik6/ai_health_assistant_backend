"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.db_url import database_host, database_ssl_connect_args
from app.core.logging import get_logger

logger = get_logger(__name__)

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None, *, echo: bool = False) -> AsyncEngine:
    """Create the process-wide async engine. Called once during application startup."""
    global engine, async_session_factory

    settings.assert_database_configured()
    url = database_url or settings.DATABASE_URL
    engine_kwargs: dict = {"echo": echo}
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        engine_kwargs.update(
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        connect_args = database_ssl_connect_args(url)
        engine_kwargs.update(
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
        )
        if connect_args:
            engine_kwargs["connect_args"] = connect_args
        logger.info("PostgreSQL host=%s ssl=%s", database_host(url) or "unknown", bool(connect_args))
    engine = create_async_engine(url, **engine_kwargs)
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return engine


def get_engine() -> AsyncEngine:
    if engine is None:
        init_engine()
    assert engine is not None
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if async_session_factory is None:
        init_engine()
    assert async_session_factory is not None
    return async_session_factory


async def dispose_engine() -> None:
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency. Commits on success, rolls back on error."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
