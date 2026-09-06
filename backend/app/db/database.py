"""SQLAlchemy engine, session factory, and Base declaration."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings

# On Vercel (serverless), each invocation is stateless — persistent connection
# pools cause "too many connections" errors on Neon/PgBouncer.
# Use NullPool in production (VERCEL=1 is set automatically by Vercel).
_is_serverless = os.environ.get("VERCEL") == "1"

if _is_serverless:
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,          # no persistent pool — open/close per request
        connect_args={
            "sslmode": "require",    # Neon requires SSL
            "connect_timeout": 10,
        },
    )
else:
    # Local dev — keep a normal pool for performance
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
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
