"""
Corpus version governance helpers.
"""

from __future__ import annotations

import logging

import redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.config import REDIS_URL
from app.models.models import CorpusState
from app.utils.cache_governance import (
    CORPUS_CURRENT_VERSION_KEY,
    delete_cache_key_sync,
    get_corpus_version_cache_ttl,
    redis_set_with_ttl_sync,
)

logger = logging.getLogger(__name__)

_sync_redis_client = None


def get_sync_redis_client():
    global _sync_redis_client

    if _sync_redis_client is None and REDIS_URL:
        try:
            _sync_redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            _sync_redis_client.ping()
        except Exception as exc:
            logger.warning("corpus_version_cache_unavailable", extra={"error": str(exc)})
            _sync_redis_client = None

    return _sync_redis_client


async def bump_corpus_version(
    session: AsyncSession,
    trigger_event: str,
    trigger_entity_id: int | None = None,
) -> int:
    """
    Atomically increments corpus version and appends an audit row.
    """
    result = await session.execute(
        text(
            """
            UPDATE corpus_state
            SET current_version = current_version + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            RETURNING current_version
            """
        )
    )
    version = result.scalar_one()
    await session.execute(
        text(
            """
            INSERT INTO corpus_versions (version, trigger_event, trigger_entity_id)
            VALUES (:version, :trigger_event, :trigger_entity_id)
            """
        ),
        {
            "version": version,
            "trigger_event": trigger_event,
            "trigger_entity_id": trigger_entity_id,
        },
    )
    return int(version)


def bump_corpus_version_sync(
    session: Session,
    trigger_event: str,
    trigger_entity_id: int | None = None,
) -> int:
    """
    Synchronous wrapper for the atomic corpus version bump.
    """
    result = session.execute(
        text(
            """
            UPDATE corpus_state
            SET current_version = current_version + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            RETURNING current_version
            """
        )
    )
    version = int(result.scalar_one())
    session.execute(
        text(
            """
            INSERT INTO corpus_versions (version, trigger_event, trigger_entity_id)
            VALUES (:version, :trigger_event, :trigger_entity_id)
            """
        ),
        {
            "version": version,
            "trigger_event": trigger_event,
            "trigger_entity_id": trigger_entity_id,
        },
    )

    redis_client = get_sync_redis_client()
    if redis_client is not None:
        delete_cache_key_sync(
            redis_client,
            CORPUS_CURRENT_VERSION_KEY,
            event="corpus_version_bumped",
            log=logger,
        )

    logger.info(
        "corpus_version_bumped",
        extra={
            "version": version,
            "trigger_event": trigger_event,
            "trigger_entity_id": trigger_entity_id,
        },
    )
    return version


def get_current_corpus_version_sync(session: Session) -> int:
    """
    Read the current corpus version, using Redis as a short-lived derived cache.
    """
    redis_client = get_sync_redis_client()
    if redis_client is not None:
        try:
            cached = redis_client.get(CORPUS_CURRENT_VERSION_KEY)
            if cached is not None:
                return int(cached)
        except Exception as exc:
            logger.warning("corpus_version_cache_read_degraded", extra={"error": str(exc)})

    version = session.execute(
        select(CorpusState.current_version).where(CorpusState.id == 1)
    ).scalar_one()

    if redis_client is not None:
        try:
            redis_set_with_ttl_sync(
                redis_client,
                CORPUS_CURRENT_VERSION_KEY,
                str(version),
                get_corpus_version_cache_ttl(),
            )
        except Exception as exc:
            logger.warning("corpus_version_cache_write_degraded", extra={"error": str(exc)})

    return int(version)
