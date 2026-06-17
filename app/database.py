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


def _normalize_pg_dsn(url: str) -> str:
    """Make a Postgres DSN safe to parse even if the password contains an
    unescaped special char (most often '@').

    urlsplit rpartitions the netloc, so it extracts host/user/password correctly;
    SQLAlchemy's string parser (and libpq) split on the FIRST '@' and fold the
    password tail into the host -> a misleading "Name or service not known" DNS
    error. If the two disagree, rebuild from the parsed components (URL.create
    re-encodes the raw password ONCE). A correctly percent-encoded password parses
    identically and is left untouched (no double-encoding).
    """
    if not url:
        return url
    from urllib.parse import parse_qsl, urlsplit
    from sqlalchemy.engine.url import URL, make_url as _make_url

    url = url.strip()
    parts = urlsplit(url)
    if not parts.hostname:
        return url
    try:
        if _make_url(url).host == parts.hostname:
            return url
    except Exception:
        pass
    try:
        return URL.create(
            drivername=parts.scheme or "postgresql",
            username=parts.username,
            password=parts.password,
            host=parts.hostname,
            port=parts.port,
            database=(parts.path or "/").lstrip("/") or None,
            query=dict(parse_qsl(parts.query)),
        ).render_as_string(hide_password=False)
    except Exception:
        return url


# Auto-encode an unescaped special char (e.g. '@') in the password so SQLAlchemy
# can't mis-parse the host (otherwise a misleading "Name or service not known").
DATABASE_URL = _normalize_pg_dsn(DATABASE_URL)


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
