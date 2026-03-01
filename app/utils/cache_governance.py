"""
Cache governance helpers for Redis-backed derived state.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import CORPUS_CURRENT_VERSION_CACHE_TTL

logger = logging.getLogger(__name__)

CORPUS_CURRENT_VERSION_KEY = "corpus_version:current"


def canonicalize_query(q: str) -> str:
    """
    Normalize query text for deterministic cache key generation.
    """
    return " ".join(sorted(q.lower().strip().split()))


def build_retrieval_cache_key(
    query: str,
    corpus_version: int,
    embed_model: str,
    rrf_config: dict,
    top_k: int,
    domain_id: str | None = None,
) -> str:
    canon = canonicalize_query(query)
    query_hash = hashlib.sha256(canon.encode()).hexdigest()[:16]
    retrieval_hash = hashlib.sha256(
        json.dumps(rrf_config, sort_keys=True).encode()
    ).hexdigest()[:8]
    scope = domain_id or "global"
    return (
        f"retrieval:v{corpus_version}:{embed_model}:{retrieval_hash}:"
        f"{top_k}:{scope}:{query_hash}"
    )


def build_doc_cache_key(doc_id: int) -> str:
    return f"doc:{doc_id}"


def build_embed_cache_key(embed_model: str, text: str) -> str:
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return f"embed:{embed_model}:{text_hash}"


async def redis_set_with_ttl(redis, key: str, value: str | bytes, ttl_seconds: int) -> None:
    """
    Refuse Redis writes that do not provide a positive TTL.
    """
    if ttl_seconds <= 0:
        raise ValueError(f"Redis write requires positive TTL, got {ttl_seconds}")
    await redis.set(key, value, ex=ttl_seconds)


def redis_set_with_ttl_sync(redis, key: str, value: str | bytes, ttl_seconds: int) -> None:
    """
    Synchronous equivalent of redis_set_with_ttl for sync Redis clients.
    """
    if ttl_seconds <= 0:
        raise ValueError(f"Redis write requires positive TTL, got {ttl_seconds}")
    redis.set(key, value, ex=ttl_seconds)


async def require_authoritative_source(
    key: str,
    cache_getter: Callable[[], Awaitable[Any]],
    db_getter: Callable[[], Awaitable[Any]],
    *,
    logger: logging.Logger,
) -> Any:
    """
    Read from cache when available, but never treat cache failure as authorization.
    """
    try:
        cached = await cache_getter()
        if cached is not None:
            return cached
    except Exception as exc:
        logger.warning(
            "Redis unavailable for authority-adjacent read: %s (fallback to DB): %s",
            key,
            exc,
        )

    return await db_getter()


def require_authoritative_source_sync(
    key: str,
    cache_getter: Callable[[], Any],
    db_getter: Callable[[], Any],
    *,
    logger: logging.Logger,
) -> Any:
    """
    Synchronous equivalent for authority-adjacent reads in sync code paths.
    """
    try:
        cached = cache_getter()
        if cached is not None:
            return cached
    except Exception as exc:
        logger.warning(
            "Redis unavailable for authority-adjacent read: %s (fallback to DB): %s",
            key,
            exc,
        )

    return db_getter()


async def delete_cache_key(redis, key: str, *, event: str, log: logging.Logger | None = None) -> None:
    """
    Delete a Redis key and log the invalidation when possible.
    """
    target_logger = log or logger
    try:
        deleted = await redis.delete(key)
        if deleted:
            target_logger.info("cache_invalidated", extra={"key": key, "event": event})
    except Exception as exc:
        target_logger.warning(
            "cache_invalidation_degraded",
            extra={"key": key, "event": event, "error": str(exc)},
        )


def delete_cache_key_sync(redis, key: str, *, event: str, log: logging.Logger | None = None) -> None:
    """
    Synchronous cache invalidation helper with logging.
    """
    target_logger = log or logger
    try:
        deleted = redis.delete(key)
        if deleted:
            target_logger.info("cache_invalidated", extra={"key": key, "event": event})
    except Exception as exc:
        target_logger.warning(
            "cache_invalidation_degraded",
            extra={"key": key, "event": event, "error": str(exc)},
        )


def serialize_json(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def get_corpus_version_cache_ttl() -> int:
    return CORPUS_CURRENT_VERSION_CACHE_TTL
