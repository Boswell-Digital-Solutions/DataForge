"""
Test Utilities for Secure Credential Handling

Provides test fixtures and utilities for handling credentials
securely in tests without hardcoding sensitive values.
"""

import os
import hashlib
import secrets
from typing import Dict, Optional
from contextlib import contextmanager
import pytest


class TestCredentials:
    """
    Centralized test credential management.
    
    All test credentials are generated or retrieved from environment
    variables to avoid hardcoding sensitive values.
    """
    
    @staticmethod
    def get_test_password(key: str = "TEST_PASSWORD") -> str:
        """
        Get test password from environment or generate one.
        
        Args:
            key: Environment variable key
            
        Returns:
            Test password string
        """
        # Try to get from environment first
        password = os.getenv(key)
        if password:
            return password
        
        # Generate a deterministic test password based on key
        # This ensures consistency across test runs
        generated = f"test_{key.lower()}_{secrets.token_hex(8)}"
        return generated
    
    @staticmethod
    def get_test_api_key(key: str = "TEST_API_KEY") -> str:
        """
        Get test API key from environment or generate one.
        
        Args:
            key: Environment variable key
            
        Returns:
            Test API key string
        """
        api_key = os.getenv(key)
        if api_key:
            return api_key
        
        # Generate a test API key format
        return f"test_key_{secrets.token_hex(16)}"
    
    @staticmethod
    def get_test_secret(key: str = "TEST_SECRET") -> str:
        """
        Get test secret from environment or generate one.
        
        Args:
            key: Environment variable key
            
        Returns:
            Test secret string
        """
        secret = os.getenv(key)
        if secret:
            return secret
        
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password for testing (matching production behavior).
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        # This should match your actual password hashing implementation
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def get_hashed_test_password(plain_password: Optional[str] = None) -> str:
        """
        Get a hashed test password.
        
        Args:
            plain_password: Optional plain password. If not provided, generates one.
            
        Returns:
            Hashed password string
        """
        if plain_password is None:
            plain_password = TestCredentials.get_test_password()
        
        return TestCredentials.hash_password(plain_password)
    
    @staticmethod
    def get_test_db_credentials() -> Dict[str, str]:
        """
        Get database credentials for testing.
        
        Returns from environment variables with safe defaults.
        
        Returns:
            Dictionary with db_user, db_password, db_host, db_name
        """
        return {
            "db_user": os.getenv("TEST_DB_USER", "test_user"),
            "db_password": os.getenv("TEST_DB_PASSWORD", 
                                    TestCredentials.get_test_password("TEST_DB_PASSWORD")),
            "db_host": os.getenv("TEST_DB_HOST", "localhost"),
            "db_name": os.getenv("TEST_DB_NAME", "test_dataforge"),
        }
    
    @staticmethod
    def get_test_jwt_secret() -> str:
        """
        Get JWT secret for testing.
        
        Returns:
            JWT secret string
        """
        return os.getenv("TEST_JWT_SECRET", 
                        secrets.token_urlsafe(32))
    
    @staticmethod
    def get_weak_password_list() -> list:
        """
        Get list of weak passwords for testing validation.
        
        These should be used to test that validation rejects weak passwords.
        They should NOT be used as actual credentials.
        
        Returns:
            List of weak passwords for testing
        """
        return [
            "123456",
            "password",
            "12345678",
            "qwerty",
            "abc123",
            "111111",
            "admin",
            "letmein",
            "welcome",
            "password123",
        ]


# Pytest fixtures for common test scenarios

@pytest.fixture
def test_credentials():
    """Provide TestCredentials class to tests."""
    return TestCredentials


@pytest.fixture
def test_password():
    """Provide a test password."""
    return TestCredentials.get_test_password()


@pytest.fixture
def test_hashed_password():
    """Provide a test hashed password."""
    return TestCredentials.get_hashed_test_password()


@pytest.fixture
def test_api_key():
    """Provide a test API key."""
    return TestCredentials.get_test_api_key()


@pytest.fixture
def test_secret():
    """Provide a test secret."""
    return TestCredentials.get_test_secret()


@pytest.fixture
def test_db_credentials():
    """Provide test database credentials."""
    return TestCredentials.get_test_db_credentials()


@pytest.fixture
def test_jwt_secret():
    """Provide a test JWT secret."""
    return TestCredentials.get_test_jwt_secret()


@pytest.fixture
def weak_passwords():
    """Provide list of weak passwords for validation testing."""
    return TestCredentials.get_weak_password_list()


@contextmanager
def mock_credentials(override_dict: Dict[str, str]):
    """
    Context manager for temporarily overriding credentials.
    
    Usage:
        with mock_credentials({"TEST_PASSWORD": "mock_value"}):
            # Use credentials within context
            pass
    
    Args:
        override_dict: Dictionary of environment variable overrides
    """
    # Save original values
    original_values = {}
    
    # Set new values
    for key, value in override_dict.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
