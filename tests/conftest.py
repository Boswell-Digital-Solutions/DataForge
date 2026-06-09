"""
Pytest configuration and shared fixtures for DataForge tests.
"""
import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, create_engine
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
os.environ.setdefault("DATAFORGE_DATABASE_URL", SQLALCHEMY_TEST_DATABASE_URL)
os.environ.setdefault("DATAFORGE_SKIP_STARTUP_DB_INIT", "1")

from app.database import Base, get_db, get_session_factory
from app.main import app
from app.models import models

# IMPORTANT:
# These imports must exist in the test bootstrap path so the runtime-promotion
# tables are registered in Base.metadata before Base.metadata.create_all(bind=engine).
from app.models.runtime_promotion_models import RuntimePromotionReceipt
from app.models.runtime_promotion_candidate_models import (
    RuntimePromotionCandidate,
    RuntimePromotionCandidateDecision,
)
from app.models.context_pack_models import ContextPack  # serve-from-precomputed context-pack store
from app.models.model_outcome_models import ModelOutcome  # durable model-learning receipts

from app.utils.auth import get_password_hash
from app.utils.rate_limit import rate_limiter as simple_rate_limiter
from tests.conftest_security import (
    TestCredentials,
    test_api_key,
    test_credentials,
    test_db_credentials,
    test_hashed_password,
    test_jwt_secret,
    test_password,
    test_secret,
    weak_passwords,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


@compiles(TSVECTOR, "sqlite")
def _compile_tsvector_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(_type, _compiler, **_kwargs):
    return "TEXT"


# Create test engine with special settings for SQLite
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database for each test.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    if session.query(models.CorpusState).filter(models.CorpusState.id == 1).first() is None:
        session.add(models.CorpusState(id=1, current_version=1))
        session.add(
            models.CorpusVersion(
                version=1,
                trigger_event="initial",
                trigger_entity_id=None,
            )
        )
        session.commit()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with database dependency override.
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_session_factory():
        return TestingSessionLocal

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = override_get_session_factory

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> models.User:
    """
    Create a test user.
    """
    user = models.User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db: Session) -> models.User:
    """
    Create a test admin user.
    """
    admin = models.User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        is_admin=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_domain(db: Session) -> models.Domain:
    """
    Create a test domain.
    """
    domain = models.Domain(
        id="test_domain",
        label="Test Domain",
        description="A test domain for testing",
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


@pytest.fixture
def test_tag(db: Session) -> models.Tag:
    """
    Create a test tag.
    """
    tag = models.Tag(name="test-tag")
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@pytest.fixture
def auth_headers(client: TestClient, test_admin: models.User) -> dict:
    """
    Get authentication headers for admin user.
    """
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "adminpassword"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_embedding():
    """
    Mock embedding vector for testing (1536 dimensions).
    """
    return [0.1] * 1536


# Environment variable overrides for testing
@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """
    Set up test environment variables.
    """
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing-only")
    monkeypatch.setenv("DATAFORGE_DATABASE_URL", SQLALCHEMY_TEST_DATABASE_URL)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def reset_in_memory_rate_limiter():
    """Prevent shared in-memory rate limit state from leaking across tests."""
    simple_rate_limiter.reset()
    yield
    simple_rate_limiter.reset()