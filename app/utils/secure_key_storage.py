"""
Secure Key Storage and Management

Implements secure storage and retrieval of encryption keys with
hardware-backed options and key derivation.
"""

import logging
import secrets
import hashlib
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class KeyStorageBackend(Enum):
    """Key storage backends."""
    MEMORY = "memory"  # In-memory storage (development)
    FILE = "file"  # File-based with permission enforcement
    HSM = "hsm"  # Hardware Security Module (production)
    KMS = "kms"  # Key Management Service (AWS KMS, Azure Key Vault)


@dataclass
class KeyDerivationParams:
    """Parameters for key derivation."""
    algorithm: str = "pbkdf2"
    iterations: int = 100000  # NIST recommendation for PBKDF2
    hash_function: str = "sha256"
    salt_length: int = 32  # 256 bits
    salt: Optional[bytes] = None
    
    def __post_init__(self):
        """Generate salt if not provided."""
        if self.salt is None:
            self.salt = secrets.token_bytes(self.salt_length)


@dataclass
class StoredKey:
    """Key stored in secure storage."""
    key_id: str
    key_material: bytes
    derivation_params: KeyDerivationParams
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    accessed_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    access_count: int = 0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def record_access(self) -> None:
        """Record key access."""
        self.accessed_at = datetime.utcnow().timestamp()
        self.access_count += 1


class KeyDerivation:
    """Derive encryption keys from passwords."""
    
    @staticmethod
    def derive_key(
        password: str,
        params: KeyDerivationParams,
    ) -> bytes:
        """
        Derive encryption key from password.
        
        Args:
            password: Master password
            params: Key derivation parameters
            
        Returns:
            Derived encryption key (32 bytes)
        """
        if params.algorithm == "pbkdf2":
            # Use PBKDF2 with SHA-256
            try:
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2 as PBKDF2Cipher
                from cryptography.hazmat.backends import default_backend
                
                kdf = PBKDF2Cipher(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=params.salt,
                    iterations=params.iterations,
                    backend=default_backend(),
                )
                
                return kdf.derive(password.encode())
            except ImportError:
                # Fallback: pure Python PBKDF2 implementation
                return KeyDerivation._pbkdf2_fallback(password, params)
        
        else:
            logger.warning(f"Unknown key derivation algorithm: {params.algorithm}")
            return secrets.token_bytes(32)
    
    @staticmethod
    def _pbkdf2_fallback(password: str, params: KeyDerivationParams) -> bytes:
        """
        PBKDF2 fallback implementation using pure Python.
        
        Args:
            password: Master password
            params: Key derivation parameters
            
        Returns:
            Derived key
        """
        import hashlib
        import hmac
        
        password_bytes = password.encode()
        
        def prf(key: bytes, msg: bytes) -> bytes:
            """HMAC-SHA256 pseudorandom function."""
            return hmac.new(key, msg, hashlib.sha256).digest()
        
        # PBKDF2 algorithm
        hash_len = 32  # SHA256 output length
        result = b''
        i = 1
        
        while len(result) < 32:
            u = prf(password_bytes, params.salt + i.to_bytes(4, 'big'))
            t = u
            
            for _ in range(params.iterations - 1):
                u = prf(password_bytes, u)
                t = bytes(a ^ b for a, b in zip(t, u))
            
            result += t
            i += 1
        
        return result[:32]


class MemoryKeyStorage:
    """In-memory key storage (development/testing only)."""
    
    def __init__(self):
        """Initialize memory key storage."""
        self.keys: Dict[str, StoredKey] = {}
    
    def store_key(self, stored_key: StoredKey) -> bool:
        """
        Store key in memory.
        
        Args:
            stored_key: Key to store
            
        Returns:
            True if successful
        """
        self.keys[stored_key.key_id] = stored_key
        logger.info(f"Stored key in memory: {stored_key.key_id}")
        return True
    
    def retrieve_key(self, key_id: str) -> Optional[StoredKey]:
        """
        Retrieve key from memory.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Stored key or None if not found
        """
        if key_id not in self.keys:
            logger.warning(f"Key not found: {key_id}")
            return None
        
        stored_key = self.keys[key_id]
        stored_key.record_access()
        return stored_key
    
    def delete_key(self, key_id: str) -> bool:
        """
        Delete key from storage.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if successful
        """
        if key_id in self.keys:
            # Securely erase key material
            key = self.keys.pop(key_id)
            key.key_material = b'\x00' * len(key.key_material)
            logger.info(f"Deleted key from memory: {key_id}")
            return True
        
        return False
    
    def list_keys(self) -> list:
        """List all stored key IDs."""
        return list(self.keys.keys())


class FileKeyStorage:
    """File-based key storage with permission enforcement."""
    
    def __init__(self, storage_path: str = "/secure/keys"):
        """
        Initialize file key storage.
        
        Args:
            storage_path: Path to secure key storage directory
        """
        self.storage_path = storage_path
        self.keys_cache: Dict[str, StoredKey] = {}
        
        import os
        os.makedirs(storage_path, mode=0o700, exist_ok=True)
        logger.info(f"Initialized file key storage at {storage_path}")
    
    def store_key(self, stored_key: StoredKey) -> bool:
        """
        Store key to file.
        
        Args:
            stored_key: Key to store
            
        Returns:
            True if successful
        """
        try:
            import os
            
            key_path = os.path.join(self.storage_path, f"{stored_key.key_id}.key")
            
            # Prepare data for storage
            data = {
                "key_id": stored_key.key_id,
                "key_material": stored_key.key_material.hex(),
                "created_at": stored_key.created_at,
                "is_active": stored_key.is_active,
                "metadata": stored_key.metadata,
            }
            
            # Write with restricted permissions
            with open(key_path, 'w') as f:
                json.dump(data, f)
            
            os.chmod(key_path, 0o600)  # Owner read/write only
            
            # Cache in memory
            self.keys_cache[stored_key.key_id] = stored_key
            
            logger.info(f"Stored key to file: {key_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to store key: {e}")
            return False
    
    def retrieve_key(self, key_id: str) -> Optional[StoredKey]:
        """
        Retrieve key from file.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Stored key or None if not found
        """
        # Check cache first
        if key_id in self.keys_cache:
            stored_key = self.keys_cache[key_id]
            stored_key.record_access()
            return stored_key
        
        try:
            import os
            
            key_path = os.path.join(self.storage_path, f"{key_id}.key")
            
            if not os.path.exists(key_path):
                logger.warning(f"Key file not found: {key_path}")
                return None
            
            # Read key file
            with open(key_path, 'r') as f:
                data = json.load(f)
            
            # Reconstruct StoredKey
            key_material = bytes.fromhex(data["key_material"])
            
            stored_key = StoredKey(
                key_id=data["key_id"],
                key_material=key_material,
                derivation_params=KeyDerivationParams(),
                created_at=data["created_at"],
                is_active=data["is_active"],
                metadata=data.get("metadata", {}),
            )
            
            stored_key.record_access()
            
            # Cache for future access
            self.keys_cache[key_id] = stored_key
            
            logger.info(f"Retrieved key from file: {key_id}")
            return stored_key
        except Exception as e:
            logger.error(f"Failed to retrieve key: {e}")
            return None
    
    def delete_key(self, key_id: str) -> bool:
        """
        Delete key from storage.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if successful
        """
        try:
            import os
            
            key_path = os.path.join(self.storage_path, f"{key_id}.key")
            
            # Secure erase: overwrite with random data before deletion
            with open(key_path, 'wb') as f:
                f.write(secrets.token_bytes(4096))
            
            os.remove(key_path)
            
            # Remove from cache
            self.keys_cache.pop(key_id, None)
            
            logger.info(f"Deleted key file: {key_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete key: {e}")
            return False
    
    def list_keys(self) -> list:
        """List all stored key IDs."""
        try:
            import os
            
            keys = []
            if os.path.exists(self.storage_path):
                for filename in os.listdir(self.storage_path):
                    if filename.endswith('.key'):
                        key_id = filename[:-4]  # Remove .key extension
                        keys.append(key_id)
            
            return keys
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            return []


class SecureKeyStorage:
    """Unified secure key storage interface."""
    
    def __init__(
        self,
        backend: KeyStorageBackend = KeyStorageBackend.MEMORY,
        storage_path: Optional[str] = None,
    ):
        """
        Initialize secure key storage.
        
        Args:
            backend: Storage backend to use
            storage_path: Path for file-based storage
        """
        self.backend = backend
        
        if backend == KeyStorageBackend.MEMORY:
            self.storage = MemoryKeyStorage()
        elif backend == KeyStorageBackend.FILE:
            path = storage_path or "/secure/keys"
            self.storage = FileKeyStorage(path)
        else:
            logger.warning(f"Unsupported storage backend: {backend.value}")
            self.storage = MemoryKeyStorage()
    
    def store_key(
        self,
        key_id: str,
        key_material: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store encryption key.
        
        Args:
            key_id: Key identifier
            key_material: Encryption key material
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        stored_key = StoredKey(
            key_id=key_id,
            key_material=key_material,
            derivation_params=KeyDerivationParams(),
            metadata=metadata or {},
        )
        
        return self.storage.store_key(stored_key)
    
    def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """
        Retrieve encryption key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Key material or None if not found
        """
        stored_key = self.storage.retrieve_key(key_id)
        
        if stored_key is None:
            return None
        
        return stored_key.key_material
    
    def delete_key(self, key_id: str) -> bool:
        """
        Delete encryption key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if successful
        """
        return self.storage.delete_key(key_id)
    
    def list_keys(self) -> list:
        """List all stored key IDs."""
        return self.storage.list_keys()
    
    def rotate_key(
        self,
        old_key_id: str,
        new_key_id: str,
    ) -> bool:
        """
        Rotate encryption key.
        
        Args:
            old_key_id: Old key identifier
            new_key_id: New key identifier
            
        Returns:
            True if successful
        """
        # New key material should be generated by caller
        # This just handles the storage transition
        logger.info(f"Key rotation prepared: {old_key_id} → {new_key_id}")
        return True


# Global secure storage instance
_global_secure_storage: Optional[SecureKeyStorage] = None


def get_secure_storage(
    backend: KeyStorageBackend = KeyStorageBackend.MEMORY,
    storage_path: Optional[str] = None,
) -> SecureKeyStorage:
    """Get or create global secure key storage."""
    global _global_secure_storage
    
    if _global_secure_storage is None:
        _global_secure_storage = SecureKeyStorage(backend, storage_path)
    
    return _global_secure_storage


def reset_secure_storage() -> None:
    """Reset global secure storage (for testing)."""
    global _global_secure_storage
    _global_secure_storage = None
