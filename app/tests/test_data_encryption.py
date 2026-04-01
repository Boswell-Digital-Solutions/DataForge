"""
from datetime import datetime, UTC
Tests for Data Encryption and Key Management (PHASE 4.2)

Comprehensive test suite for encryption, key rotation, and PII protection.
"""

import pytest
from app.utils.data_encryption import (
    EncryptionAlgorithm,
    KeyRotationPolicy,
    EncryptionKey,
    FieldLevelEncryption,
    KeyManager,
    DatabaseEncryption,
    BackupEncryption,
    PIIDetector,
    get_key_manager,
    reset_key_manager,
)
from app.utils.secure_key_storage import (
    KeyStorageBackend,
    KeyDerivationParams,
    KeyDerivation,
    MemoryKeyStorage,
    SecureKeyStorage,
    get_secure_storage,
    reset_secure_storage,
)


class TestFieldLevelEncryption:
    """Tests for field-level encryption."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.master_key = b'a' * 32  # 256-bit key
        self.encryptor = FieldLevelEncryption(self.master_key)
    
    def test_encrypt_string_field(self):
        """Test encrypting string field."""
        plaintext = "sensitive@example.com"
        ciphertext = self.encryptor.encrypt_field(plaintext)
        
        assert ciphertext is not None
        assert ciphertext != plaintext
        assert len(ciphertext) > 0
    
    def test_encrypt_dict_field(self):
        """Test encrypting dictionary field."""
        plaintext = {"email": "user@example.com", "phone": "555-1234"}
        ciphertext = self.encryptor.encrypt_field(plaintext)
        
        assert ciphertext is not None
        assert isinstance(ciphertext, str)
    
    def test_decrypt_field(self):
        """Test decrypting field."""
        plaintext = "sensitive@example.com"
        ciphertext = self.encryptor.encrypt_field(plaintext)
        decrypted = self.encryptor.decrypt_field(ciphertext)
        
        assert decrypted == plaintext
    
    def test_decrypt_dict_field(self):
        """Test decrypting dictionary field."""
        plaintext = {"email": "user@example.com", "phone": "555-1234"}
        ciphertext = self.encryptor.encrypt_field(plaintext)
        decrypted = self.encryptor.decrypt_field(ciphertext)
        
        assert decrypted == plaintext
    
    def test_decrypt_invalid_ciphertext(self):
        """Test decrypting invalid ciphertext."""
        invalid_ciphertext = "aW52YWxpZA=="  # Invalid base64
        decrypted = self.encryptor.decrypt_field(invalid_ciphertext)
        
        assert decrypted is None


class TestEncryptionKey:
    """Tests for encryption key."""
    
    def test_key_creation(self):
        """Test creating encryption key."""
        key = EncryptionKey(
            key_id="test-key",
            key_material=b'a' * 32,
            algorithm=EncryptionAlgorithm.FERNET,
        )
        
        assert key.key_id == "test-key"
        assert key.is_active
    
    def test_key_rotation_check_no_rotation(self):
        """Test key rotation policy NEVER."""
        key = EncryptionKey(
            key_id="test-key",
            key_material=b'a' * 32,
            algorithm=EncryptionAlgorithm.FERNET,
            rotation_policy=KeyRotationPolicy.NEVER,
        )
        
        assert not key.is_rotated()
    
    def test_key_rotation_check_quarterly(self):
        """Test key rotation policy QUARTERLY."""
        key = EncryptionKey(
            key_id="test-key",
            key_material=b'a' * 32,
            algorithm=EncryptionAlgorithm.FERNET,
            rotation_policy=KeyRotationPolicy.QUARTERLY,
        )
        
        # Fresh key should not need rotation
        assert not key.is_rotated()
        
        # Simulate old key (120 days)
        from datetime import datetime
        key.created_at = (
            datetime.now(UTC).timestamp() - (120 * 86400)
        )
        
        # Should need rotation (>90 days)
        assert key.is_rotated()
    
    def test_mark_key_rotated(self):
        """Test marking key as rotated."""
        key = EncryptionKey(
            key_id="test-key",
            key_material=b'a' * 32,
            algorithm=EncryptionAlgorithm.FERNET,
            rotation_policy=KeyRotationPolicy.QUARTERLY,
        )
        
        assert key.rotated_at is None
        
        key.mark_rotated()
        
        assert key.rotated_at is not None


class TestKeyManager:
    """Tests for key manager."""
    
    def setup_method(self):
        """Reset manager before each test."""
        reset_key_manager()
        self.manager = get_key_manager()
    
    def test_generate_key(self):
        """Test generating encryption key."""
        key = self.manager.generate_key(
            key_id="test-key",
            algorithm=EncryptionAlgorithm.FERNET,
        )
        
        assert key.key_id == "test-key"
        assert key.is_active
    
    def test_get_active_key(self):
        """Test getting active key."""
        key = self.manager.generate_key("key-1")
        active_key = self.manager.get_active_key()
        
        assert active_key is not None
        assert active_key.key_id == "key-1"
    
    def test_get_specific_key(self):
        """Test getting specific key."""
        key = self.manager.generate_key("key-1")
        retrieved_key = self.manager.get_key("key-1")
        
        assert retrieved_key is not None
        assert retrieved_key.key_id == "key-1"
    
    def test_rotate_key(self):
        """Test key rotation."""
        original_key = self.manager.generate_key("key-1")
        original_active_key_id = self.manager.active_key_id
        
        new_key = self.manager.rotate_key("key-1")
        
        assert new_key is not None
        assert new_key.key_id != original_key.key_id
        assert self.manager.active_key_id != original_active_key_id
        assert not original_key.is_active
    
    def test_check_rotation_needed(self):
        """Test checking if keys need rotation."""
        key = self.manager.generate_key(
            "key-1",
            rotation_policy=KeyRotationPolicy.QUARTERLY,
        )
        
        # Fresh key should not need rotation
        assert len(self.manager.check_rotation_needed()) == 0
        
        # Simulate old key
        from datetime import datetime
        key.created_at = (
            datetime.now(UTC).timestamp() - (120 * 86400)
        )
        
        # Should need rotation now
        assert "key-1" in self.manager.check_rotation_needed()


class TestDatabaseEncryption:
    """Tests for database record encryption."""
    
    def setup_method(self):
        """Setup test fixtures."""
        reset_key_manager()
        self.manager = get_key_manager()
        self.db_encryption = DatabaseEncryption(self.manager)
        
        # Generate a key
        self.manager.generate_key("encryption-key")
    
    def test_encrypt_record(self):
        """Test encrypting database record."""
        record = {
            "user_id": "123",
            "email": "user@example.com",
            "name": "John Doe",
        }
        
        encrypted_record = self.db_encryption.encrypt_record(
            record,
            fields_to_encrypt=["email"],
        )
        
        assert "email" in encrypted_record
        assert isinstance(encrypted_record["email"], dict)
        assert encrypted_record["email"]["__encrypted__"]
    
    def test_decrypt_record(self):
        """Test decrypting database record."""
        original_record = {
            "user_id": "123",
            "email": "user@example.com",
            "name": "John Doe",
        }
        
        encrypted_record = self.db_encryption.encrypt_record(
            original_record,
            fields_to_encrypt=["email"],
        )
        
        decrypted_record = self.db_encryption.decrypt_record(encrypted_record)
        
        assert decrypted_record["email"] == original_record["email"]
        assert decrypted_record["user_id"] == original_record["user_id"]
    
    def test_encrypt_multiple_fields(self):
        """Test encrypting multiple fields."""
        record = {
            "user_id": "123",
            "email": "user@example.com",
            "phone": "555-1234",
            "ssn": "123-45-6789",
        }
        
        encrypted_record = self.db_encryption.encrypt_record(
            record,
            fields_to_encrypt=["email", "phone", "ssn"],
        )
        
        assert encrypted_record["email"]["__encrypted__"]
        assert encrypted_record["phone"]["__encrypted__"]
        assert encrypted_record["ssn"]["__encrypted__"]


class TestBackupEncryption:
    """Tests for backup encryption."""
    
    def setup_method(self):
        """Setup test fixtures."""
        reset_key_manager()
        self.manager = get_key_manager()
        self.backup_encryption = BackupEncryption(self.manager)
        
        # Generate a key
        self.manager.generate_key("backup-key")
    
    def test_encrypt_backup(self):
        """Test encrypting backup data."""
        backup_data = "CREATE TABLE users (id INT, email VARCHAR(255));"
        
        encrypted_data = self.backup_encryption.encrypt_backup(backup_data)
        
        assert encrypted_data is not None
        assert encrypted_data.ciphertext != backup_data
    
    def test_decrypt_backup(self):
        """Test decrypting backup data."""
        backup_data = "CREATE TABLE users (id INT, email VARCHAR(255));"
        
        encrypted_data = self.backup_encryption.encrypt_backup(backup_data)
        decrypted_data = self.backup_encryption.decrypt_backup(encrypted_data)
        
        assert decrypted_data == backup_data
    
    def test_backup_encryption_with_metadata(self):
        """Test backup encryption stores metadata."""
        backup_data = "SELECT * FROM users;"
        
        encrypted_data = self.backup_encryption.encrypt_backup(backup_data)
        
        assert encrypted_data.key_id is not None
        assert encrypted_data.algorithm is not None
        assert encrypted_data.timestamp is not None


class TestPIIDetector:
    """Tests for PII detection."""
    
    def test_detect_email_field(self):
        """Test detecting email PII field."""
        assert PIIDetector.is_likely_pii("email")
        assert PIIDetector.is_likely_pii("user_email")
        assert PIIDetector.is_likely_pii("primary_email")
    
    def test_detect_phone_field(self):
        """Test detecting phone PII field."""
        assert PIIDetector.is_likely_pii("phone")
        assert PIIDetector.is_likely_pii("phone_number")
        assert PIIDetector.is_likely_pii("telephone")
    
    def test_detect_ssn_field(self):
        """Test detecting SSN PII field."""
        assert PIIDetector.is_likely_pii("ssn")
        assert PIIDetector.is_likely_pii("social_security_number")
    
    def test_detect_non_pii_field(self):
        """Test non-PII fields not detected."""
        assert not PIIDetector.is_likely_pii("user_id")
        assert not PIIDetector.is_likely_pii("created_at")
        assert not PIIDetector.is_likely_pii("status")
    
    def test_get_pii_fields(self):
        """Test getting all PII fields from record."""
        record = {
            "user_id": "123",
            "email": "user@example.com",
            "phone": "555-1234",
            "created_at": "2025-11-21",
        }
        
        pii_fields = PIIDetector.get_pii_fields(record)
        
        assert "email" in pii_fields
        assert "phone" in pii_fields
        assert "user_id" not in pii_fields
        assert "created_at" not in pii_fields


class TestMemoryKeyStorage:
    """Tests for memory-based key storage."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.storage = MemoryKeyStorage()
    
    def test_store_and_retrieve_key(self):
        """Test storing and retrieving key."""
        from app.utils.secure_key_storage import StoredKey
        
        key = StoredKey(
            key_id="test-key",
            key_material=b'a' * 32,
            derivation_params=KeyDerivationParams(),
        )
        
        assert self.storage.store_key(key)
        
        retrieved = self.storage.retrieve_key("test-key")
        assert retrieved is not None
        assert retrieved.key_id == "test-key"
    
    def test_delete_key(self):
        """Test deleting key."""
        from app.utils.secure_key_storage import StoredKey
        
        key = StoredKey(
            key_id="test-key",
            key_material=b'a' * 32,
            derivation_params=KeyDerivationParams(),
        )
        
        self.storage.store_key(key)
        assert self.storage.delete_key("test-key")
        assert self.storage.retrieve_key("test-key") is None
    
    def test_list_keys(self):
        """Test listing all keys."""
        from app.utils.secure_key_storage import StoredKey
        
        key1 = StoredKey(
            key_id="key-1",
            key_material=b'a' * 32,
            derivation_params=KeyDerivationParams(),
        )
        key2 = StoredKey(
            key_id="key-2",
            key_material=b'b' * 32,
            derivation_params=KeyDerivationParams(),
        )
        
        self.storage.store_key(key1)
        self.storage.store_key(key2)
        
        keys = self.storage.list_keys()
        assert len(keys) == 2
        assert "key-1" in keys
        assert "key-2" in keys


class TestSecureKeyStorage:
    """Tests for unified secure key storage."""
    
    def setup_method(self):
        """Reset storage before each test."""
        reset_secure_storage()
        self.storage = get_secure_storage(KeyStorageBackend.MEMORY)
    
    def test_store_and_retrieve_key(self):
        """Test storing and retrieving key."""
        key_material = b'a' * 32
        
        assert self.storage.store_key("test-key", key_material)
        
        retrieved = self.storage.retrieve_key("test-key")
        assert retrieved == key_material
    
    def test_delete_key(self):
        """Test deleting key."""
        key_material = b'a' * 32
        
        self.storage.store_key("test-key", key_material)
        assert self.storage.delete_key("test-key")
        assert self.storage.retrieve_key("test-key") is None
    
    def test_list_keys(self):
        """Test listing keys."""
        self.storage.store_key("key-1", b'a' * 32)
        self.storage.store_key("key-2", b'b' * 32)
        
        keys = self.storage.list_keys()
        assert len(keys) == 2
        assert "key-1" in keys
        assert "key-2" in keys


class TestKeyDerivation:
    """Tests for key derivation."""
    
    def test_derive_key_pbkdf2(self):
        """Test key derivation with PBKDF2."""
        params = KeyDerivationParams(algorithm="pbkdf2")
        
        derived_key = KeyDerivation.derive_key("password", params)
        
        assert derived_key is not None
        assert len(derived_key) == 32  # 256 bits
    
    def test_derive_key_consistency(self):
        """Test that same password produces same key with same salt."""
        params = KeyDerivationParams(algorithm="pbkdf2")
        
        key1 = KeyDerivation.derive_key("password", params)
        key2 = KeyDerivation.derive_key("password", params)
        
        assert key1 == key2
    
    def test_derive_key_different_password(self):
        """Test that different passwords produce different keys."""
        params = KeyDerivationParams(algorithm="pbkdf2")
        
        key1 = KeyDerivation.derive_key("password1", params)
        
        # New params with different salt
        params2 = KeyDerivationParams(algorithm="pbkdf2")
        key2 = KeyDerivation.derive_key("password2", params2)
        
        assert key1 != key2


class TestIntegrationDataSecurity:
    """Integration tests for complete data security workflows."""
    
    def setup_method(self):
        """Setup test fixtures."""
        reset_key_manager()
        self.manager = get_key_manager()
        self.db_encryption = DatabaseEncryption(self.manager)
        self.manager.generate_key("main-key")
    
    def test_complete_user_record_encryption(self):
        """Test complete workflow for encrypting user record."""
        # Create user record
        user_record = {
            "user_id": "user-123",
            "email": "john.doe@example.com",
            "phone": "555-1234",
            "address": "123 Main St",
            "created_at": "2025-11-21",
        }
        
        # Detect PII fields
        pii_fields = PIIDetector.get_pii_fields(user_record)
        
        # Encrypt PII
        encrypted_record = self.db_encryption.encrypt_record(
            user_record,
            fields_to_encrypt=pii_fields,
        )
        
        # Verify PII encrypted
        assert encrypted_record["email"]["__encrypted__"]
        assert encrypted_record["phone"]["__encrypted__"]
        
        # Decrypt and verify
        decrypted_record = self.db_encryption.decrypt_record(encrypted_record)
        
        assert decrypted_record["email"] == user_record["email"]
        assert decrypted_record["phone"] == user_record["phone"]
        assert decrypted_record["created_at"] == user_record["created_at"]
    
    def test_key_rotation_workflow(self):
        """Test complete key rotation workflow."""
        # Create initial record with first key
        user_record = {"user_id": "123", "email": "user@example.com"}
        
        encrypted_v1 = self.db_encryption.encrypt_record(
            user_record,
            fields_to_encrypt=["email"],
        )
        
        # Rotate key
        new_key = self.manager.rotate_key("main-key")
        assert new_key is not None
        
        # Encrypt with new key
        encrypted_v2 = self.db_encryption.encrypt_record(
            user_record,
            fields_to_encrypt=["email"],
        )
        
        # Both should decrypt to original
        decrypted_v1 = self.db_encryption.decrypt_record(encrypted_v1)
        decrypted_v2 = self.db_encryption.decrypt_record(encrypted_v2)
        
        assert decrypted_v1["email"] == user_record["email"]
        assert decrypted_v2["email"] == user_record["email"]
