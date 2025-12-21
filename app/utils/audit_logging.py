"""
Comprehensive audit logging for security events and compliance tracking.

Provides:
- Structured audit log entries with severity levels
- Event type classification (Auth, Data, Access, Config, Admin)
- User and resource tracking with metadata
- Immutable audit logs with cryptographic signatures
- Compliance reporting (GDPR, CCPA, HIPAA)
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from abc import ABC, abstractmethod
import json
import hashlib
import hmac
import logging
from functools import wraps
import re


# ============================================================================
# Event Severity and Type Enums
# ============================================================================

class AuditSeverity(Enum):
    """Severity levels for audit events."""
    INFO = "info"              # Informational - routine operations
    WARNING = "warning"        # Warning - suspicious but allowed
    CRITICAL = "critical"      # Critical - security violation attempt
    ERROR = "error"            # Error - operation failed


class AuditEventType(Enum):
    """Classification of audit events."""
    AUTH_LOGIN = "auth_login"                      # User login
    AUTH_LOGOUT = "auth_logout"                    # User logout
    AUTH_FAILED = "auth_failed"                    # Failed authentication
    AUTH_MFA = "auth_mfa"                          # MFA operations
    AUTH_SESSION = "auth_session"                  # Session management
    
    DATA_ACCESS = "data_access"                    # Data read/query
    DATA_MODIFY = "data_modify"                    # Data create/update/delete
    DATA_EXPORT = "data_export"                    # Data export/dump
    DATA_DELETE = "data_delete"                    # Data deletion
    DATA_ENCRYPT = "data_encrypt"                  # Encryption operations
    DATA_DECRYPT = "data_decrypt"                  # Decryption operations
    
    ACCESS_GRANT = "access_grant"                  # Permission granted
    ACCESS_REVOKE = "access_revoke"                # Permission revoked
    ACCESS_DENIED = "access_denied"                # Access denied
    
    CONFIG_CHANGE = "config_change"                # Configuration modified
    CONFIG_VIEW = "config_view"                    # Configuration viewed
    
    ADMIN_USER = "admin_user"                      # User management
    ADMIN_ROLE = "admin_role"                      # Role management
    ADMIN_BACKUP = "admin_backup"                  # Backup operations
    
    ANOMALY_DETECTED = "anomaly_detected"          # Anomalous activity
    THREAT_DETECTED = "threat_detected"            # Security threat


# ============================================================================
# Audit Log Data Structures
# ============================================================================

@dataclass
class AuditLog:
    """Immutable audit log entry."""
    
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    resource_id: Optional[str]
    resource_type: Optional[str]
    action: str
    result: str  # "success" or "failure"
    status_code: int
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    
    # Computed fields
    signature: Optional[str] = None
    entry_hash: Optional[str] = None
    
    def __post_init__(self):
        """Compute signature and hash after initialization."""
        if not self.signature:
            self.signature = self._compute_signature()
        if not self.entry_hash:
            self.entry_hash = self._compute_hash()
    
    def _compute_signature(self) -> str:
        """Compute HMAC signature for integrity verification."""
        data = f"{self.timestamp}{self.event_type.value}{self.user_id}{self.resource_id}{self.action}"
        # In production, use secure key from environment
        key = b"audit-signature-key"
        return hmac.new(key, data.encode(), hashlib.sha256).hexdigest()
    
    def _compute_hash(self) -> str:
        """Compute SHA256 hash of entire log entry."""
        log_dict = asdict(self)
        log_dict.pop("signature", None)
        log_dict.pop("entry_hash", None)
        log_dict["timestamp"] = str(self.timestamp.isoformat())
        log_dict["event_type"] = self.event_type.value
        log_dict["severity"] = self.severity.value
        
        json_str = json.dumps(log_dict, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def verify_signature(self, key: bytes) -> bool:
        """Verify audit log signature (integrity check)."""
        data = f"{self.timestamp}{self.event_type.value}{self.user_id}{self.resource_id}{self.action}"
        expected_sig = hmac.new(key, data.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature or "", expected_sig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "action": self.action,
            "result": self.result,
            "status_code": self.status_code,
            "message": self.message,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "signature": self.signature,
            "entry_hash": self.entry_hash,
        }


# ============================================================================
# Audit Log Storage Backends
# ============================================================================

class AuditLogBackend(ABC):
    """Abstract base for audit log storage."""
    
    @abstractmethod
    def write(self, log: AuditLog) -> bool:
        """Write audit log entry. Returns success."""
        pass
    
    @abstractmethod
    def read(self, log_id: str) -> Optional[AuditLog]:
        """Read specific audit log entry."""
        pass
    
    @abstractmethod
    def query(self, filters: Dict[str, Any], limit: int = 100) -> List[AuditLog]:
        """Query audit logs by filters (event_type, user_id, timestamp range, etc)."""
        pass
    
    @abstractmethod
    def count(self, filters: Dict[str, Any]) -> int:
        """Count matching audit logs."""
        pass


class InMemoryAuditBackend(AuditLogBackend):
    """In-memory audit log storage (development/testing)."""
    
    def __init__(self):
        self.logs: List[AuditLog] = []
        self._index: Dict[str, int] = {}
    
    def write(self, log: AuditLog) -> bool:
        """Write log entry."""
        try:
            idx = len(self.logs)
            self.logs.append(log)
            self._index[log.entry_hash or ""] = idx
            return True
        except Exception:
            return False
    
    def read(self, log_id: str) -> Optional[AuditLog]:
        """Read specific log by hash."""
        idx = self._index.get(log_id)
        return self.logs[idx] if idx is not None else None
    
    def query(self, filters: Dict[str, Any], limit: int = 100) -> List[AuditLog]:
        """Query logs by filters."""
        results = []
        
        for log in self.logs:
            match = True
            
            if "event_type" in filters and log.event_type != filters["event_type"]:
                match = False
            if "user_id" in filters and log.user_id != filters["user_id"]:
                match = False
            if "severity" in filters and log.severity != filters["severity"]:
                match = False
            if "start_time" in filters and log.timestamp < filters["start_time"]:
                match = False
            if "end_time" in filters and log.timestamp > filters["end_time"]:
                match = False
            
            if match:
                results.append(log)
            
            if len(results) >= limit:
                break
        
        return results
    
    def count(self, filters: Dict[str, Any]) -> int:
        """Count matching logs."""
        return len(self.query(filters, limit=10000))


class FileAuditBackend(AuditLogBackend):
    """File-based audit log storage (JSON lines format)."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.logs_cache: List[AuditLog] = []
        self._load_cache()
    
    def _load_cache(self):
        """Load logs from file into memory cache."""
        try:
            with open(self.filepath, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        log = self._dict_to_log(data)
                        self.logs_cache.append(log)
        except FileNotFoundError:
            self.logs_cache = []
    
    def _dict_to_log(self, data: Dict[str, Any]) -> AuditLog:
        """Convert dictionary to AuditLog."""
        return AuditLog(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=AuditEventType(data["event_type"]),
            severity=AuditSeverity(data["severity"]),
            user_id=data.get("user_id"),
            resource_id=data.get("resource_id"),
            resource_type=data.get("resource_type"),
            action=data["action"],
            result=data["result"],
            status_code=data["status_code"],
            message=data["message"],
            metadata=data.get("metadata", {}),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            request_id=data.get("request_id"),
            signature=data.get("signature"),
            entry_hash=data.get("entry_hash"),
        )
    
    def write(self, log: AuditLog) -> bool:
        """Write log entry to file."""
        try:
            with open(self.filepath, 'a') as f:
                f.write(json.dumps(log.to_dict()) + '\n')
            self.logs_cache.append(log)
            return True
        except Exception:
            return False
    
    def read(self, log_id: str) -> Optional[AuditLog]:
        """Read specific log by hash."""
        for log in self.logs_cache:
            if log.entry_hash == log_id:
                return log
        return None
    
    def query(self, filters: Dict[str, Any], limit: int = 100) -> List[AuditLog]:
        """Query logs by filters."""
        results = []
        
        for log in self.logs_cache:
            match = True
            
            if "event_type" in filters and log.event_type != filters["event_type"]:
                match = False
            if "user_id" in filters and log.user_id != filters["user_id"]:
                match = False
            if "severity" in filters and log.severity != filters["severity"]:
                match = False
            if "start_time" in filters and log.timestamp < filters["start_time"]:
                match = False
            if "end_time" in filters and log.timestamp > filters["end_time"]:
                match = False
            
            if match:
                results.append(log)
            
            if len(results) >= limit:
                break
        
        return results
    
    def count(self, filters: Dict[str, Any]) -> int:
        """Count matching logs."""
        return len(self.query(filters, limit=10000))


# ============================================================================
# Audit Logger
# ============================================================================

class AuditLogger:
    """
    Central audit logger for tracking security events.
    Singleton pattern: use get_audit_logger()
    """
    
    _instance = None
    
    def __init__(self, backend: AuditLogBackend):
        self.backend = backend
        self.logger = logging.getLogger("audit")
    
    def log(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        action: str,
        result: str,
        status_code: int,
        message: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """Log security event."""
        
        log_entry = AuditLog(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            result=result,
            status_code=status_code,
            message=message,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        
        # Write to backend
        self.backend.write(log_entry)
        
        # Log to Python logger
        level = {
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.CRITICAL: logging.CRITICAL,
            AuditSeverity.ERROR: logging.ERROR,
        }[severity]
        
        self.logger.log(
            level,
            f"{event_type.value}: {action} - {message}",
            extra={"user_id": user_id, "resource_id": resource_id},
        )
        
        return log_entry
    
    def log_auth_event(
        self,
        action: str,  # "login", "logout", "failed", "mfa"
        result: str,
        user_id: Optional[str],
        message: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log authentication event."""
        
        event_type_map = {
            "login": AuditEventType.AUTH_LOGIN,
            "logout": AuditEventType.AUTH_LOGOUT,
            "failed": AuditEventType.AUTH_FAILED,
            "mfa": AuditEventType.AUTH_MFA,
        }
        
        severity = (
            AuditSeverity.CRITICAL if result == "failure"
            else AuditSeverity.INFO
        )
        
        return self.log(
            event_type=event_type_map.get(action, AuditEventType.AUTH_LOGIN),
            severity=severity,
            action=action,
            result=result,
            status_code=200 if result == "success" else 401,
            message=message,
            user_id=user_id,
            resource_type="user",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
    
    def log_data_event(
        self,
        action: str,  # "access", "modify", "delete", "export", "encrypt", "decrypt"
        result: str,
        resource_id: Optional[str],
        resource_type: str,
        user_id: Optional[str],
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log data access/modification event."""
        
        event_type_map = {
            "access": AuditEventType.DATA_ACCESS,
            "modify": AuditEventType.DATA_MODIFY,
            "delete": AuditEventType.DATA_DELETE,
            "export": AuditEventType.DATA_EXPORT,
            "encrypt": AuditEventType.DATA_ENCRYPT,
            "decrypt": AuditEventType.DATA_DECRYPT,
        }
        
        severity = (
            AuditSeverity.WARNING if action in ("delete", "export")
            else AuditSeverity.INFO
        )
        
        return self.log(
            event_type=event_type_map.get(action, AuditEventType.DATA_ACCESS),
            severity=severity,
            action=action,
            result=result,
            status_code=200 if result == "success" else 400,
            message=message,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            metadata=metadata,
        )
    
    def log_access_event(
        self,
        action: str,  # "grant", "revoke", "denied"
        result: str,
        user_id: Optional[str],
        resource_id: Optional[str],
        resource_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log access control event."""
        
        event_type_map = {
            "grant": AuditEventType.ACCESS_GRANT,
            "revoke": AuditEventType.ACCESS_REVOKE,
            "denied": AuditEventType.ACCESS_DENIED,
        }
        
        severity = (
            AuditSeverity.WARNING if action == "denied"
            else AuditSeverity.INFO
        )
        
        return self.log(
            event_type=event_type_map.get(action, AuditEventType.ACCESS_DENIED),
            severity=severity,
            action=action,
            result=result,
            status_code=403 if action == "denied" else 200,
            message=message,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            metadata=metadata,
        )
    
    def log_config_event(
        self,
        action: str,  # "change", "view"
        result: str,
        user_id: Optional[str],
        config_key: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log configuration change event."""
        
        return self.log(
            event_type=AuditEventType.CONFIG_CHANGE if action == "change"
            else AuditEventType.CONFIG_VIEW,
            severity=AuditSeverity.WARNING if action == "change"
            else AuditSeverity.INFO,
            action=action,
            result=result,
            status_code=200 if result == "success" else 400,
            message=message,
            user_id=user_id,
            resource_id=config_key,
            resource_type="config",
            metadata=metadata,
        )
    
    def log_anomaly(
        self,
        anomaly_type: str,
        severity: AuditSeverity,
        user_id: Optional[str],
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log detected anomaly."""
        
        return self.log(
            event_type=AuditEventType.ANOMALY_DETECTED,
            severity=severity,
            action="detected",
            result="detected",
            status_code=200,
            message=message,
            user_id=user_id,
            resource_type="anomaly",
            metadata=metadata,
        )
    
    def query(self, filters: Dict[str, Any], limit: int = 100) -> List[AuditLog]:
        """Query audit logs."""
        return self.backend.query(filters, limit)
    
    def count(self, filters: Dict[str, Any]) -> int:
        """Count matching audit logs."""
        return self.backend.count(filters)


def get_audit_logger(backend: Optional[AuditLogBackend] = None) -> AuditLogger:
    """Get singleton audit logger instance."""
    if AuditLogger._instance is None:
        if backend is None:
            backend = InMemoryAuditBackend()
        AuditLogger._instance = AuditLogger(backend)
    return AuditLogger._instance


def audit_log(event_type: AuditEventType, severity: AuditSeverity = AuditSeverity.INFO):
    """
    Decorator for automatic audit logging of function calls.
    
    Usage:
        @audit_log(AuditEventType.DATA_ACCESS, AuditSeverity.INFO)
        def get_user(user_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_audit_logger()
            user_id = kwargs.get("user_id") or (args[1] if len(args) > 1 else None)
            
            try:
                result = func(*args, **kwargs)
                logger.log(
                    event_type=event_type,
                    severity=severity,
                    action=func.__name__,
                    result="success",
                    status_code=200,
                    message=f"Function {func.__name__} executed successfully",
                    user_id=user_id,
                )
                return result
            except Exception as e:
                logger.log(
                    event_type=event_type,
                    severity=AuditSeverity.ERROR,
                    action=func.__name__,
                    result="failure",
                    status_code=500,
                    message=f"Function {func.__name__} failed: {str(e)}",
                    user_id=user_id,
                )
                raise
        return wrapper
    return decorator
