from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.settings import get_settings


def _sync_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return url


@lru_cache
def get_sync_engine() -> Engine:
    settings = get_settings()
    url = _sync_database_url(settings.database_url)
    connect_args: dict[str, bool | int] = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False, "timeout": 15}
    return create_engine(url, pool_pre_ping=not url.startswith("sqlite"), connect_args=connect_args)


@lru_cache
def get_sync_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_sync_engine(), expire_on_commit=False)


def sync_session() -> Session:
    return get_sync_session_factory()()
