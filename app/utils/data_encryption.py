"""
Data Encryption and Key Management

Implements encryption at rest, field-level encryption for PII, and
secure key management for sensitive data protection.
"""

import logging
import secrets
import hashlib
import base64
import json
import hmac
from typing import Any, Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    Fernet = None
    InvalidToken = Exception

logger = logging.getLogger(__name__)


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "aes-256-gcm"  # AES with Galois Counter Mode
    FERNET = "fernet"  # Symmetric encryption with authentication


class KeyRotationPolicy(Enum):
    """Key rotation policies."""
    NEVER = "never"
    YEARLY = "yearly"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"


@dataclass
class EncryptionKey:
    """Encryption key with metadata."""
    key_id: str
    key_material: bytes
    algorithm: EncryptionAlgorithm
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    rotation_policy: KeyRotationPolicy = KeyRotationPolicy.QUARTERLY
    rotated_at: Optional[float] = None
    is_active: bool = True
    
    def is_rotated(self) -> bool:
        """Check if key needs rotation based on policy."""
        if self.rotation_policy == KeyRotationPolicy.NEVER:
            return False
        
        # Calculate days since creation/last rotation
        reference_time = self.rotated_at or self.created_at
        days_elapsed = (datetime.utcnow().timestamp() - reference_time) / 86400
        
        policy_days = {
            KeyRotationPolicy.YEARLY: 365,
            KeyRotationPolicy.QUARTERLY: 90,
            KeyRotationPolicy.MONTHLY: 30,
            KeyRotationPolicy.WEEKLY: 7,
        }
        
        threshold = policy_days.get(self.rotation_policy, float('inf'))
        return days_elapsed >= threshold
    
    def mark_rotated(self) -> None:
        """Mark key as rotated."""
        self.rotated_at = datetime.utcnow().timestamp()


@dataclass
class EncryptedData:
    """Encrypted data with metadata."""
    ciphertext: str  # Base64-encoded encrypted data
    key_id: str  # ID of key used for encryption
    algorithm: EncryptionAlgorithm
    iv: Optional[str] = None  # Base64-encoded initialization vector
    tag: Optional[str] = None  # Authentication tag for GCM mode
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())


class FieldLevelEncryption:
    """Encrypt/decrypt individual fields or objects."""
    
    def __init__(self, master_key: bytes):
        """
        Initialize field encryption.
        
        Args:
            master_key: Master encryption key (32 bytes for AES-256)
        """
        self.cipher_suite = None
        if Fernet is not None:
            try:
                self.cipher_suite = Fernet(base64.urlsafe_b64encode(master_key[:32]))
            except Exception as e:
                logger.error(f"Failed to initialize Fernet cipher: {e}")
                self.cipher_suite = None
        else:
            logger.warning("Cryptography library not available, using XOR fallback")
            self.master_key = master_key[:32]
    
    def encrypt_field(self, data: Any) -> Optional[str]:
        """
        Encrypt a single field.
        
        Args:
            data: Data to encrypt (will be JSON serialized if not string)
            
        Returns:
            Base64-encoded encrypted data or None if encryption failed
        """
        try:
            # Convert to JSON string if needed
            if isinstance(data, str):
                plaintext = data.encode()
            else:
                plaintext = json.dumps(data).encode()
            
            if self.cipher_suite is not None:
                # Use Fernet encryption if available
                ciphertext = self.cipher_suite.encrypt(plaintext)
                return base64.b64encode(ciphertext).decode()
            else:
                # Fallback: XOR with key material
                return self._xor_encrypt(plaintext)
        except Exception as e:
            logger.error(f"Field encryption failed: {e}")
            return None
    
    def decrypt_field(self, encrypted_data: str) -> Optional[Any]:
        """
        Decrypt a single field.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Decrypted data or None if decryption failed
        """
        try:
            if self.cipher_suite is not None:
                # Use Fernet decryption if available
                ciphertext = base64.b64decode(encrypted_data)
                plaintext = self.cipher_suite.decrypt(ciphertext)
            else:
                # Fallback: XOR with key material
                plaintext = self._xor_decrypt(encrypted_data)
            
            # Try to parse as JSON
            try:
                return json.loads(plaintext.decode())
            except json.JSONDecodeError:
                # Return as string if not JSON
                return plaintext.decode()
        except (InvalidToken if Fernet is not None else Exception) as e:
            logger.error("Invalid encryption token, data may be corrupted")
            return None
        except Exception as e:
            logger.error(f"Field decryption failed: {e}")
            return None
    
    def _xor_encrypt(self, plaintext: bytes) -> str:
        """Fallback XOR encryption with key."""
        key = self.master_key
        ciphertext = bytes(
            p ^ k for p, k in zip(plaintext, (key * ((len(plaintext) // len(key)) + 1)))
        )
        return base64.b64encode(ciphertext).decode()
    
    def _xor_decrypt(self, encrypted_data: str) -> bytes:
        """Fallback XOR decryption with key."""
        key = self.master_key
        ciphertext = base64.b64decode(encrypted_data)
        plaintext = bytes(
            c ^ k for c, k in zip(ciphertext, (key * ((len(ciphertext) // len(key)) + 1)))
        )
        return plaintext


class KeyManager:
    """Manage encryption keys, rotation, and versioning."""
    
    def __init__(self, master_password: str, max_keys: int = 100):
        """
        Initialize key manager.
        
        Args:
            master_password: Master password for deriving keys
            max_keys: Maximum number of keys to store
        """
        self.master_password = master_password
        self.max_keys = max_keys
        self.keys: Dict[str, EncryptionKey] = {}
        self.active_key_id: Optional[str] = None
    
    def generate_key(
        self,
        key_id: str,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.FERNET,
        rotation_policy: KeyRotationPolicy = KeyRotationPolicy.QUARTERLY,
    ) -> EncryptionKey:
        """
        Generate new encryption key.
        
        Args:
            key_id: Unique key identifier
            algorithm: Encryption algorithm
            rotation_policy: Key rotation policy
            
        Returns:
            New encryption key
        """
        # Generate random key material
        key_material = secrets.token_bytes(32)  # 256 bits
        
        key = EncryptionKey(
            key_id=key_id,
            key_material=key_material,
            algorithm=algorithm,
            rotation_policy=rotation_policy,
        )
        
        self.keys[key_id] = key
        
        # Set as active if first key
        if self.active_key_id is None:
            self.active_key_id = key_id
        
        # Cleanup if too many keys
        if len(self.keys) > self.max_keys:
            self._cleanup_old_keys()
        
        logger.info(f"Generated encryption key: {key_id}")
        return key
    
    def rotate_key(self, key_id: str) -> Optional[EncryptionKey]:
        """
        Rotate encryption key.
        
        Args:
            key_id: Key to rotate
            
        Returns:
            New key or None if original key not found
        """
        if key_id not in self.keys:
            logger.warning(f"Key not found for rotation: {key_id}")
            return None
        
        old_key = self.keys[key_id]
        
        # Generate new key with same ID (versioned)
        new_key_id = f"{key_id}_v{int(datetime.utcnow().timestamp())}"
        new_key = self.generate_key(
            key_id=new_key_id,
            algorithm=old_key.algorithm,
            rotation_policy=old_key.rotation_policy,
        )
        
        # Mark old key as inactive
        old_key.is_active = False
        
        # Set new key as active
        self.active_key_id = new_key_id
        
        logger.info(f"Rotated key {key_id} → {new_key_id}")
        return new_key
    
    def get_active_key(self) -> Optional[EncryptionKey]:
        """Get currently active encryption key."""
        if self.active_key_id is None:
            return None
        return self.keys.get(self.active_key_id)
    
    def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """Get specific encryption key."""
        return self.keys.get(key_id)
    
    def check_rotation_needed(self) -> List[str]:
        """
        Check which keys need rotation.
        
        Returns:
            List of key IDs that need rotation
        """
        keys_to_rotate = []
        
        for key_id, key in self.keys.items():
            if key.is_active and key.is_rotated():
                keys_to_rotate.append(key_id)
        
        return keys_to_rotate
    
    def _cleanup_old_keys(self) -> None:
        """Remove oldest inactive keys."""
        inactive_keys = [
            (key_id, key) for key_id, key in self.keys.items()
            if not key.is_active
        ]
        
        # Sort by creation time and remove oldest
        inactive_keys.sort(key=lambda x: x[1].created_at)
        
        for key_id, _ in inactive_keys[:len(inactive_keys) - 5]:
            self.keys.pop(key_id, None)
        
        logger.info(f"Cleaned up {len(inactive_keys) - 5} old keys")


class DatabaseEncryption:
    """Encryption for database records."""
    
    def __init__(self, key_manager: KeyManager):
        """
        Initialize database encryption.
        
        Args:
            key_manager: Key manager instance
        """
        self.key_manager = key_manager
    
    def encrypt_record(
        self,
        record: Dict[str, Any],
        fields_to_encrypt: List[str],
    ) -> Dict[str, Any]:
        """
        Encrypt specified fields in a record.
        
        Args:
            record: Database record
            fields_to_encrypt: List of field names to encrypt
            
        Returns:
            Record with encrypted fields
        """
        active_key = self.key_manager.get_active_key()
        if active_key is None:
            logger.warning("No active encryption key")
            return record
        
        # Create copy to avoid modifying original
        encrypted_record = record.copy()
        
        # Initialize field encryption
        field_encryptor = FieldLevelEncryption(active_key.key_material)
        
        # Encrypt specified fields
        for field_name in fields_to_encrypt:
            if field_name in encrypted_record:
                original_value = encrypted_record[field_name]
                encrypted_value = field_encryptor.encrypt_field(original_value)
                
                if encrypted_value:
                    # Store encrypted data with metadata
                    encrypted_record[field_name] = {
                        "__encrypted__": True,
                        "__key_id__": active_key.key_id,
                        "__algorithm__": active_key.algorithm.value,
                        "__ciphertext__": encrypted_value,
                    }
        
        return encrypted_record
    
    def decrypt_record(
        self,
        record: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Decrypt encrypted fields in a record.
        
        Args:
            record: Database record with encrypted fields
            
        Returns:
            Record with decrypted fields
        """
        decrypted_record = record.copy()
        
        for field_name, field_value in record.items():
            if isinstance(field_value, dict) and field_value.get("__encrypted__"):
                # Extract metadata
                key_id = field_value.get("__key_id__")
                ciphertext = field_value.get("__ciphertext__")
                
                # Get decryption key
                encryption_key = self.key_manager.get_key(key_id)
                if encryption_key is None:
                    logger.warning(f"Encryption key not found: {key_id}")
                    decrypted_record[field_name] = None
                    continue
                
                # Initialize field decryption
                field_decryptor = FieldLevelEncryption(encryption_key.key_material)
                
                # Decrypt
                decrypted_value = field_decryptor.decrypt_field(ciphertext)
                decrypted_record[field_name] = decrypted_value
        
        return decrypted_record


class BackupEncryption:
    """Encryption for database backups."""
    
    def __init__(self, key_manager: KeyManager):
        """
        Initialize backup encryption.
        
        Args:
            key_manager: Key manager instance
        """
        self.key_manager = key_manager
    
    def encrypt_backup(
        self,
        backup_data: str,
    ) -> Optional[EncryptedData]:
        """
        Encrypt backup data.
        
        Args:
            backup_data: Unencrypted backup SQL/JSON
            
        Returns:
            Encrypted data with metadata or None if encryption failed
        """
        active_key = self.key_manager.get_active_key()
        if active_key is None:
            logger.warning("No active encryption key")
            return None
        
        try:
            field_encryptor = FieldLevelEncryption(active_key.key_material)
            ciphertext = field_encryptor.encrypt_field(backup_data)
            
            if ciphertext is None:
                return None
            
            return EncryptedData(
                ciphertext=ciphertext,
                key_id=active_key.key_id,
                algorithm=active_key.algorithm,
            )
        except Exception as e:
            logger.error(f"Backup encryption failed: {e}")
            return None
    
    def decrypt_backup(
        self,
        encrypted_data: EncryptedData,
    ) -> Optional[str]:
        """
        Decrypt backup data.
        
        Args:
            encrypted_data: Encrypted backup with metadata
            
        Returns:
            Decrypted backup data or None if decryption failed
        """
        # Get decryption key
        encryption_key = self.key_manager.get_key(encrypted_data.key_id)
        if encryption_key is None:
            logger.warning(f"Encryption key not found: {encrypted_data.key_id}")
            return None
        
        try:
            field_decryptor = FieldLevelEncryption(encryption_key.key_material)
            decrypted = field_decryptor.decrypt_field(encrypted_data.ciphertext)
            
            if decrypted is None:
                return None
            
            # Return as string if possible
            return str(decrypted) if decrypted else None
        except Exception as e:
            logger.error(f"Backup decryption failed: {e}")
            return None


class PIIDetector:
    """Detect Personally Identifiable Information (PII) fields."""
    
    # Common PII field names
    PII_PATTERNS = {
        "email": r".*email.*",
        "phone": r".*phone.*|.*tel.*",
        "ssn": r".*ssn.*|.*social.*security.*",
        "credit_card": r".*card.*|.*cc_.*|.*credit.*",
        "password": r".*password.*|.*passwd.*",
        "address": r".*address.*|.*street.*",
        "name": r".*name.*|.*full_name.*",
        "dob": r".*dob.*|.*date_of_birth.*|.*birthdate.*",
        "ip": r".*ip_.*|.*ip_address.*",
        "api_key": r".*api.*key.*|.*token.*",
    }
    
    @classmethod
    def is_likely_pii(cls, field_name: str) -> bool:
        """
        Detect if field name suggests PII.
        
        Args:
            field_name: Field name to check
            
        Returns:
            True if field appears to contain PII
        """
        field_lower = field_name.lower()
        
        for pii_type, pattern in cls.PII_PATTERNS.items():
            import re
            if re.match(pattern, field_lower):
                return True
        
        return False
    
    @classmethod
    def get_pii_fields(cls, record: Dict[str, Any]) -> List[str]:
        """
        Get likely PII fields from record.
        
        Args:
            record: Database record
            
        Returns:
            List of field names likely containing PII
        """
        pii_fields = []
        
        for field_name in record.keys():
            if cls.is_likely_pii(field_name):
                pii_fields.append(field_name)
        
        return pii_fields


# Global key manager instance
_global_key_manager: Optional[KeyManager] = None


def get_key_manager(master_password: str = "default-master-password") -> KeyManager:
    """Get or create global key manager."""
    global _global_key_manager
    
    if _global_key_manager is None:
        _global_key_manager = KeyManager(master_password)
    
    return _global_key_manager


def reset_key_manager() -> None:
    """Reset global key manager (for testing)."""
    global _global_key_manager
    _global_key_manager = None
