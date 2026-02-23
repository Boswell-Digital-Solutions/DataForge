"""
Pytest configuration and shared fixtures for DataForge tests.
"""
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import models
from app.utils.auth import get_password_hash
from tests.conftest_security import (
    TestCredentials,
    test_credentials,
    test_password,
    test_hashed_password,
    test_api_key,
    test_secret,
    test_db_credentials,
    test_jwt_secret,
    weak_passwords,
)

# Use in-memory SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

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
    
    app.dependency_overrides[get_db] = override_get_db
    
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
        is_admin=False
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
        is_admin=True
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
        description="A test domain for testing"
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
        data={"username": "admin", "password": "adminpassword"}
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

