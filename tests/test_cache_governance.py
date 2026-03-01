"""
Tests for cache governance helpers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from app.utils.cache_governance import (
    build_embed_cache_key,
    build_retrieval_cache_key,
    canonicalize_query,
    redis_set_with_ttl,
    redis_set_with_ttl_sync,
    require_authoritative_source,
    require_authoritative_source_sync,
)


@pytest.mark.asyncio
async def test_redis_set_with_ttl_rejects_zero_ttl() -> None:
    redis_client = AsyncMock()

    with pytest.raises(ValueError):
        await redis_set_with_ttl(redis_client, "key", "value", 0)


@pytest.mark.asyncio
async def test_redis_set_with_ttl_sets_explicit_ttl() -> None:
    redis_client = AsyncMock()

    await redis_set_with_ttl(redis_client, "key", "value", 60)

    redis_client.set.assert_awaited_once_with("key", "value", ex=60)


def test_redis_set_with_ttl_sync_sets_explicit_ttl() -> None:
    redis_client = Mock()

    redis_set_with_ttl_sync(redis_client, "key", "value", 30)

    redis_client.set.assert_called_once_with("key", "value", ex=30)


def test_cache_key_determinism() -> None:
    key_one = build_retrieval_cache_key(
        query="Hello World",
        corpus_version=1,
        embed_model="voyage-large-2",
        rrf_config={"alpha": 1, "beta": 2},
        top_k=5,
        domain_id="tenant-a",
    )
    key_two = build_retrieval_cache_key(
        query="world hello",
        corpus_version=1,
        embed_model="voyage-large-2",
        rrf_config={"beta": 2, "alpha": 1},
        top_k=5,
        domain_id="tenant-a",
    )
    bumped = build_retrieval_cache_key(
        query="world hello",
        corpus_version=2,
        embed_model="voyage-large-2",
        rrf_config={"alpha": 1, "beta": 2},
        top_k=5,
        domain_id="tenant-a",
    )

    assert canonicalize_query("Hello World") == canonicalize_query("world hello")
    assert key_one == key_two
    assert key_one != bumped


def test_embed_cache_key_is_deterministic() -> None:
    assert build_embed_cache_key("voyage-large-2", "abc") == build_embed_cache_key(
        "voyage-large-2", "abc"
    )


@pytest.mark.asyncio
async def test_require_authoritative_source_falls_back_to_db_on_cache_error() -> None:
    cache_getter = AsyncMock(side_effect=RuntimeError("redis down"))
    db_getter = AsyncMock(return_value={"allowed": False})
    test_logger = Mock()

    result = await require_authoritative_source(
        "authority:key",
        cache_getter,
        db_getter,
        logger=test_logger,
    )

    assert result == {"allowed": False}
    db_getter.assert_awaited_once()
    test_logger.warning.assert_called_once()


def test_require_authoritative_source_sync_falls_back_to_db_on_cache_miss() -> None:
    cache_getter = Mock(return_value=None)
    db_getter = Mock(return_value={"allowed": False})
    test_logger = Mock()

    result = require_authoritative_source_sync(
        "authority:key",
        cache_getter,
        db_getter,
        logger=test_logger,
    )

    assert result == {"allowed": False}
    db_getter.assert_called_once()
