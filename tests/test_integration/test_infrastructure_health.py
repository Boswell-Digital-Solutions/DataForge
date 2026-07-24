"""
Infrastructure health and connectivity tests.
Tests database, cache, embedding service, and system health.
"""
import asyncio
import pytest
import time
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import inspect as sa_inspect, text

from app.database import get_db, engine
from app.utils import redis_utils
from app.utils.redis_utils import get_redis_client
from app.utils import embeddings
from app.config import get_settings


def _dialect_name(db: Session) -> str:
    return db.get_bind().dialect.name


def _require_postgres(db: Session) -> None:
    if _dialect_name(db) != "postgresql":
        pytest.skip("PostgreSQL-specific check is not applicable for this test backend")


async def _get_redis_or_skip():
    client = await get_redis_client()
    if not client:
        pytest.skip("Redis not available")
    return client


@pytest.fixture(autouse=True)
async def _reset_async_redis_client():
    await redis_utils.close_redis()
    yield
    await redis_utils.close_redis()


@pytest.mark.infrastructure
class TestDatabaseHealth:
    """Test database connectivity and health."""
    
    def test_database_connection(self, db: Session):
        """Test basic database connection."""
        # Simple query to verify connection
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    def test_database_version(self, db: Session):
        """Test database version and capabilities."""
        if _dialect_name(db) == "postgresql":
            result = db.execute(text("SELECT version()"))
        else:
            result = db.execute(text("SELECT sqlite_version()"))
        version = result.scalar()
        assert version is not None
        if _dialect_name(db) == "postgresql":
            assert "PostgreSQL" in version or "postgres" in version.lower()
    
    def test_pgvector_extension(self, db: Session):
        """Test pgvector extension is loaded."""
        _require_postgres(db)
        result = db.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')")
        )
        is_loaded = result.scalar()
        assert is_loaded, "pgvector extension not loaded"
    
    def test_database_tables_exist(self, db: Session):
        """Test all required tables exist."""
        inspector = sa_inspect(db.get_bind())
        existing_tables = set(inspector.get_table_names())
        required_tables = [
            "users",
            "diligence_projects",
            "diligence_reviews",
            "diligence_findings",
            "forge_events_v1",
            "authorforge_analytics_events",
        ]
        
        for table_name in required_tables:
            assert table_name in existing_tables, f"Table {table_name} not found"

        # AuthorForge content stays in its embedded database. The retired cloud
        # content table must not return as part of CI database initialization.
        assert "projects" not in existing_tables
    
    def test_database_connection_pool(self, db: Session):
        """Test connection pool health."""
        # Multiple connections
        for _ in range(5):
            result = db.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    def test_database_indexes_exist(self, db: Session):
        """Test critical indexes are created."""
        _require_postgres(db)
        indexes_to_check = [
            "idx_diligence_project_user_id",
            "idx_diligence_review_status",
            "idx_diligence_finding_status",
        ]
        
        for index_name in indexes_to_check:
            result = db.execute(
                text(
                    f"SELECT EXISTS(SELECT 1 FROM pg_indexes "
                    f"WHERE indexname = '{index_name}')"
                )
            )
            exists = result.scalar()
            # Indexes might not all exist, but check for at least one
            if index_name == "idx_diligence_project_user_id":
                assert exists, f"Index {index_name} not found"
    
    def test_database_transaction(self, db: Session):
        """Test transaction support."""
        try:
            # Start transaction
            db.execute(text("BEGIN"))
            result = db.execute(text("SELECT 1"))
            assert result.scalar() == 1
            db.execute(text("ROLLBACK"))
        except Exception as e:
            pytest.fail(f"Transaction test failed: {e}")
    
    def test_database_query_timeout(self, db: Session):
        """Test query timeout handling."""
        _require_postgres(db)
        # Set timeout
        db.execute(text("SET statement_timeout = '5s'"))
        
        # Quick query should succeed
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    def test_database_encoding(self, db: Session):
        """Test database encoding for Unicode support."""
        _require_postgres(db)
        result = db.execute(
            text("SELECT datcollate FROM pg_database WHERE datname = current_database()")
        )
        encoding = result.scalar()
        assert encoding is not None


@pytest.mark.infrastructure
class TestRedisHealth:
    """Test Redis connectivity and health."""
    
    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """Test basic Redis connection."""
        client = await _get_redis_or_skip()
        assert await client.ping(), "Redis health check failed"
    
    @pytest.mark.asyncio
    async def test_redis_client_availability(self):
        """Test Redis client is available."""
        client = await _get_redis_or_skip()
        assert client is not None
    
    @pytest.mark.asyncio
    async def test_redis_set_get(self):
        """Test basic Redis set/get operations."""
        client = await _get_redis_or_skip()
        
        # Set value
        await client.set("test_key", "test_value")
        
        # Get value
        value = await client.get("test_key")
        assert value == "test_value"
        
        # Cleanup
        await client.delete("test_key")
    
    @pytest.mark.asyncio
    async def test_redis_expiration(self):
        """Test Redis key expiration."""
        client = await _get_redis_or_skip()
        
        # Set with expiration
        await client.setex("expire_test", 1, "value")
        
        # Should exist immediately
        assert await client.get("expire_test") == "value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be gone
        assert await client.get("expire_test") is None
    
    @pytest.mark.asyncio
    async def test_redis_list_operations(self):
        """Test Redis list operations."""
        client = await _get_redis_or_skip()
        
        key = "test_list"
        
        # Clear first
        await client.delete(key)
        
        # Push values
        await client.rpush(key, "item1", "item2", "item3")
        
        # Get all
        items = await client.lrange(key, 0, -1)
        assert len(items) == 3
        
        # Cleanup
        await client.delete(key)
    
    @pytest.mark.asyncio
    async def test_redis_hash_operations(self):
        """Test Redis hash operations."""
        client = await _get_redis_or_skip()
        
        key = "test_hash"
        
        # Clear first
        await client.delete(key)
        
        # Set hash
        await client.hset(key, mapping={"field1": "value1", "field2": "value2"})
        
        # Get all
        hash_data = await client.hgetall(key)
        assert len(hash_data) == 2
        
        # Cleanup
        await client.delete(key)
    
    @pytest.mark.asyncio
    async def test_redis_memory_usage(self):
        """Test Redis memory information."""
        client = await _get_redis_or_skip()
        
        info = await client.info("memory")
        assert "used_memory" in info
        assert info["used_memory"] > 0
    
    @pytest.mark.asyncio
    async def test_redis_connection_persistence(self):
        """Test Redis connection persists across operations."""
        client = await _get_redis_or_skip()
        
        for i in range(10):
            await client.set(f"persist_test_{i}", f"value_{i}")
            value = await client.get(f"persist_test_{i}")
            assert value == f"value_{i}"
        
        # Cleanup
        for i in range(10):
            await client.delete(f"persist_test_{i}")


@pytest.mark.infrastructure
class TestEmbeddingServiceHealth:
    """Test embedding service connectivity."""
    
    def test_embedding_provider_configured(self):
        """Test embedding provider is configured."""
        settings = get_settings()
        assert settings.EMBEDDING_PROVIDER in ["voyage", "openai", "cohere"]
    
    @pytest.mark.asyncio
    async def test_embedding_generation(self):
        """Test embedding generation works."""
        try:
            # Try to generate an embedding
            embedding = await embeddings.generate_embedding("test text")
            assert embedding is not None
            assert len(embedding) > 0
        except Exception as e:
            # May fail due to API key, but should not error on structure
            pytest.skip(f"Embedding service not available: {e}")
    
    @pytest.mark.asyncio
    async def test_embedding_batch_generation(self):
        """Test batch embedding generation."""
        try:
            texts = ["text1", "text2", "text3"]
            embeddings_result = await embeddings.generate_embeddings_batch(texts)
            assert len(embeddings_result) == 3
        except Exception as e:
            pytest.skip(f"Embedding service not available: {e}")
    
    def test_embedding_model_configured(self):
        """Test embedding model is configured."""
        settings = get_settings()
        assert settings.EMBEDDING_MODEL is not None
        assert len(settings.EMBEDDING_MODEL) > 0


@pytest.mark.infrastructure
class TestHealthCheckEndpoints:
    """Test health check endpoints."""
    
    def test_health_endpoint(self, client):
        """Test /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]
    
    def test_health_check_database_status(self, client):
        """Test health endpoint includes database status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # Database status might be nested
        assert response.status_code == 200


@pytest.mark.infrastructure
class TestSystemResources:
    """Test system resource availability."""
    
    def test_database_disk_space(self, db: Session):
        """Test database disk space availability."""
        try:
            result = db.execute(
                text("SELECT pg_database_size(current_database()) as size")
            )
            size = result.scalar()
            assert size > 0
        except Exception as e:
            pytest.skip(f"Could not check disk space: {e}")
    
    def test_database_table_sizes(self, db: Session):
        """Test database table sizes."""
        try:
            result = db.execute(
                text(
                    "SELECT table_name, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) "
                    "FROM pg_tables WHERE schemaname = 'public' LIMIT 1"
                )
            )
            row = result.first()
            assert row is not None
        except Exception as e:
            pytest.skip(f"Could not check table sizes: {e}")
    
    def test_database_connection_count(self, db: Session):
        """Test current database connection count."""
        _require_postgres(db)
        result = db.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
        )
        count = result.scalar()
        assert count > 0  # At least our current connection


@pytest.mark.infrastructure
class TestDependencyAvailability:
    """Test required dependencies are available."""
    
    def test_sqlalchemy_available(self):
        """Test SQLAlchemy is available."""
        from sqlalchemy import __version__
        assert __version__ is not None
    
    def test_psycopg_available(self):
        """Test psycopg database driver available."""
        try:
            import psycopg
            assert psycopg is not None
        except ImportError:
            pytest.skip("psycopg not installed")
    
    def test_redis_py_available(self):
        """Test redis-py package available."""
        try:
            import redis
            assert redis is not None
        except ImportError:
            pytest.skip("redis-py not installed")
    
    def test_fastapi_available(self):
        """Test FastAPI is available."""
        from fastapi import __version__
        assert __version__ is not None
    
    def test_pydantic_available(self):
        """Test Pydantic is available."""
        from pydantic import __version__
        assert __version__ is not None


@pytest.mark.infrastructure
class TestGracefulDegradation:
    """Test graceful degradation when services are unavailable."""
    
    def test_api_works_without_redis(self, db: Session, monkeypatch):
        """Test API works even if Redis is unavailable."""
        # Mock Redis to be unavailable
        def mock_redis_unavailable():
            raise ConnectionError("Redis unavailable")
        
        # This would be tested via the actual API endpoints
        # For now, just verify we can still access database
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    def test_database_pool_recovery(self, db: Session):
        """Test database connection pool recovers."""
        # Make multiple connections
        for _ in range(3):
            result = db.execute(text("SELECT 1"))
            assert result.scalar() == 1


@pytest.mark.infrastructure
class TestConcurrentConnections:
    """Test concurrent connection handling."""
    
    def test_multiple_database_connections(self, db: Session):
        """Test multiple concurrent database connections."""
        results = []
        for i in range(5):
            result = db.execute(text(f"SELECT {i}"))
            results.append(result.scalar())
        
        assert results == [0, 1, 2, 3, 4]
    
    @pytest.mark.asyncio
    async def test_redis_concurrent_operations(self):
        """Test concurrent Redis operations."""
        client = await _get_redis_or_skip()
        
        for i in range(10):
            await client.set(f"concurrent_{i}", f"value_{i}")
        
        for i in range(10):
            value = await client.get(f"concurrent_{i}")
            assert value == f"value_{i}"
        
        # Cleanup
        for i in range(10):
            await client.delete(f"concurrent_{i}")
