"""SQLAlchemy engine, session factory, and Base declaration."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings

# On Railway/Vercel (serverless), use NullPool.
# RAILWAY_ENVIRONMENT is set automatically by Railway.
_is_serverless = os.environ.get("VERCEL") == "1" or os.environ.get("RAILWAY_ENVIRONMENT") is not None

# SQLAlchemy needs the right driver prefix:
# - psycopg2  → postgresql+psycopg2://
# - pg8000    → postgresql+pg8000://
# We auto-detect by trying psycopg2 first, fall back to pg8000.
def _get_db_url():
    url = settings.DATABASE_URL
    # If already has a driver specified, use as-is
    if "+pg8000" in url or "+psycopg2" in url:
        return url
    # pg8000 doesn't accept sslmode/channel_binding as URL params — strip them
    # and handle SSL via connect_args instead
    import re
    url = re.sub(r'[?&]sslmode=[^&]*', '', url)
    url = re.sub(r'[?&]channel_binding=[^&]*', '', url)
    url = re.sub(r'\?$', '', url)  # remove trailing ?
    return url.replace("postgresql://", "postgresql+pg8000://", 1)

_db_url = _get_db_url()

# pg8000 needs ssl passed as connect_arg, not URL param
_connect_args = {"ssl_context": True} if "neon.tech" in (_db_url or "") else {}

if _is_serverless:
    engine = create_engine(
        _db_url,
        poolclass=NullPool,
        connect_args=_connect_args,
    )
else:
    engine = create_engine(
        _db_url,
        poolclass=QueuePool,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args=_connect_args,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
