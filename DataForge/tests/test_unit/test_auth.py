"""
Unit tests for authentication utilities.
"""
import pytest
from datetime import timedelta
from jose import jwt

from app.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    authenticate_user,
    get_user_by_username,
    SECRET_KEY,
    ALGORITHM
)
from app.models import models


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_password_hash_and_verify(self):
        """Test that password hashing and verification work correctly."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Verification should succeed
        assert verify_password(password, hashed) is True
    
    def test_wrong_password_fails(self):
        """Test that wrong password fails verification."""
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "samepassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and validation."""
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        # Token should be a string
        assert isinstance(token, str)
        
        # Should be able to decode it
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert "exp" in payload
    
    def test_create_token_with_expiration(self):
        """Test token creation with custom expiration."""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
    
    def test_token_contains_expiration(self):
        """Test that token contains expiration claim."""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload


@pytest.mark.unit
class TestUserAuthentication:
    """Test user authentication functions."""
    
    def test_get_user_by_username(self, db, test_user):
        """Test retrieving user by username."""
        user = get_user_by_username(db, "testuser")
        
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
    
    def test_get_nonexistent_user(self, db):
        """Test retrieving non-existent user returns None."""
        user = get_user_by_username(db, "nonexistent")
        assert user is None
    
    def test_authenticate_user_success(self, db, test_user):
        """Test successful user authentication."""
        user = authenticate_user(db, "testuser", "testpassword")
        
        assert user is not False
        assert user.username == "testuser"
    
    def test_authenticate_user_wrong_password(self, db, test_user):
        """Test authentication fails with wrong password."""
        user = authenticate_user(db, "testuser", "wrongpassword")
        assert user is False
    
    def test_authenticate_nonexistent_user(self, db):
        """Test authentication fails for non-existent user."""
        user = authenticate_user(db, "nonexistent", "password")
        assert user is False


@pytest.mark.unit
class TestUserModel:
    """Test User model."""
    
    def test_create_user(self, db):
        """Test creating a user."""
        user = models.User(
            username="newuser",
            email="new@example.com",
            hashed_password=get_password_hash("password"),
            is_active=True,
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.id is not None
        assert user.username == "newuser"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is not None
    
    def test_user_unique_username(self, db, test_user):
        """Test that username must be unique."""
        duplicate_user = models.User(
            username="testuser",  # Same as test_user
            email="different@example.com",
            hashed_password=get_password_hash("password")
        )
        db.add(duplicate_user)
        
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            db.commit()

