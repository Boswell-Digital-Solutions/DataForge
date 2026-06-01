import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from dotenv import load_dotenv

from app.config import (
    DATABASE_URL,
    DB_CONNECT_TIMEOUT_SECONDS,
    DB_IDLE_IN_TX_TIMEOUT_MS,
    DB_LOCK_TIMEOUT_MS,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE_SECONDS,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT_SECONDS,
    DB_STATEMENT_TIMEOUT_MS,
)

load_dotenv()


def _build_connect_args(database_url: str) -> dict[str, object]:
    url = make_url(database_url)
    if url.get_backend_name().startswith("sqlite"):
        return {}

    options = [
        f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
        f"-c lock_timeout={DB_LOCK_TIMEOUT_MS}",
        f"-c idle_in_transaction_session_timeout={DB_IDLE_IN_TX_TIMEOUT_MS}",
    ]
    connect_args: dict[str, object] = {
        "connect_timeout": DB_CONNECT_TIMEOUT_SECONDS,
        "options": " ".join(options),
    }

    # Enforce TLS for remote databases (e.g. Supabase). Local hosts default to
    # "prefer" (use TLS if offered) so local Postgres without SSL still works;
    # remote hosts default to "require". Both can be overridden via DB_SSLMODE,
    # and an sslmode already present in the URL always wins.
    if "sslmode" not in url.query:
        host = (url.host or "").lower()
        is_local = host in {"localhost", "127.0.0.1", "::1", ""}
        default_sslmode = "prefer" if is_local else "require"
        connect_args["sslmode"] = os.getenv("DB_SSLMODE", default_sslmode)

    return connect_args


def _build_engine_kwargs(database_url: str) -> dict[str, object]:
    url = make_url(database_url)
    kwargs: dict[str, object] = {
        "pool_pre_ping": True,
        "connect_args": _build_connect_args(database_url),
    }
    if not url.get_backend_name().startswith("sqlite"):
        kwargs.update(
            {
                "pool_size": DB_POOL_SIZE,
                "max_overflow": DB_MAX_OVERFLOW,
                "pool_timeout": DB_POOL_TIMEOUT_SECONDS,
                "pool_recycle": DB_POOL_RECYCLE_SECONDS,
            }
        )
    return kwargs


engine = create_engine(DATABASE_URL, **_build_engine_kwargs(DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_session_factory():
    """Dependency for accessing the configured SQLAlchemy session factory."""
    return SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
