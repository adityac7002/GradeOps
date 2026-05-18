"""
Database engine and session management.

Key design decisions:
- Async-ready session factory (can switch to async SQLAlchemy later)
- Proper connection pooling for PostgreSQL
- SQLite-safe configuration for development
- Session dependency that auto-closes on request completion
"""
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool

from backend.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Engine configuration ────────────────────────────────────────────────────

_connect_args = {}
_pool_kwargs = {}

if settings.is_sqlite:
    _connect_args["check_same_thread"] = False
    _pool_kwargs["poolclass"] = StaticPool  # Single connection for SQLite
else:
    # PostgreSQL / MySQL pool settings
    _pool_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,       # Verify connections before use
        "pool_recycle": 1800,        # Recycle connections every 30 min
    })

engine = create_engine(
    settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite"),  # Sync engine
    connect_args=_connect_args,
    echo=settings.DATABASE_ECHO,
    **_pool_kwargs,
)

# Enable WAL mode for SQLite (better concurrent read performance)
if settings.is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Declarative base ────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Dependency ───────────────────────────────────────────────────────────────

def get_db():
    """FastAPI dependency that yields a database session and auto-closes it."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
