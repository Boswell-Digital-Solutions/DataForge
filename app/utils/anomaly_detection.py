"""
Security anomaly detection and threat identification.

Provides:
- User behavior baseline and deviation detection
- Impossible travel detection (geographic anomalies)
- Brute force attack detection
- Data exfiltration detection
- Suspicious pattern matching
- Real-time threat alerting
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Set, Optional, Tuple
import re
from collections import defaultdict
from abc import ABC, abstractmethod


# ============================================================================
# Anomaly Types
# ============================================================================

class AnomalyType(Enum):
    """Classification of detected anomalies."""
    IMPOSSIBLE_TRAVEL = "impossible_travel"        # Geographically impossible login
    BRUTE_FORCE = "brute_force"                    # Multiple failed auth attempts
    DATA_EXFILTRATION = "data_exfiltration"        # Unusual data access/export
    PRIVILEGE_ESCALATION = "privilege_escalation"  # Unusual permission changes
    SUSPICIOUS_PATTERN = "suspicious_pattern"      # Custom rule matching
    ANOMALOUS_TIME = "anomalous_time"              # Access at unusual time
    BULK_OPERATION = "bulk_operation"              # Unusual bulk data access
    CREDENTIAL_STUFFING = "credential_stuffing"    # Multiple account login attempts


class ThreatLevel(Enum):
    """Threat severity level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class UserBehaviorProfile:
    """Baseline user behavior for anomaly detection."""
    
    user_id: str
    last_login: Optional[datetime] = None
    last_location: Optional[Dict[str, any]] = None
    typical_login_hours: Set[int] = field(default_factory=set)  # 0-23
    typical_ip_addresses: Set[str] = field(default_factory=set)
    typical_user_agents: Set[str] = field(default_factory=set)
    typical_data_access_volume: float = 0.0  # GB per day
    devices_used: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    access_patterns: Dict[str, int] = field(default_factory=dict)  # resource -> count


@dataclass
class DetectedAnomaly:
    """Detected security anomaly."""
    
    anomaly_type: AnomalyType
    threat_level: ThreatLevel
    user_id: str
    timestamp: datetime
    message: str
    metadata: Dict[str, any]
    confidence_score: float  # 0.0-1.0
    recommendations: List[str] = field(default_factory=list)


@dataclass
class AnomalyThreshold:
    """Configurable threshold for anomaly detection."""
    
    anomaly_type: AnomalyType
    threshold: float
    window_minutes: int = 60
    enabled: bool = True


# ============================================================================
# Behavior Baseline
# ============================================================================

class UserBehaviorBaseline:
    """Track and analyze user behavior patterns."""
    
    def __init__(self):
        self.profiles: Dict[str, UserBehaviorProfile] = {}
        self.login_history: Dict[str, List[Tuple[datetime, Dict]]] = defaultdict(list)
        self.access_history: Dict[str, List[Tuple[datetime, str, int]]] = defaultdict(list)
    
    def get_or_create_profile(self, user_id: str) -> UserBehaviorProfile:
        """Get existing or create new user behavior profile."""
        if user_id not in self.profiles:
            self.profiles[user_id] = UserBehaviorProfile(user_id=user_id)
        return self.profiles[user_id]
    
    def record_login(
        self,
        user_id: str,
        timestamp: datetime,
        location: Optional[Dict[str, any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
    ):
        """Record user login event for baseline analysis."""
        profile = self.get_or_create_profile(user_id)
        
        # Update last login
        profile.last_login = timestamp
        profile.last_location = location
        
        # Add to login history
        login_data = {
            "location": location,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_id": device_id,
        }
        self.login_history[user_id].append((timestamp, login_data))
        
        # Update typical patterns
        if ip_address:
            profile.typical_ip_addresses.add(ip_address)
        if user_agent:
            profile.typical_user_agents.add(user_agent)
        if device_id:
            profile.devices_used.add(device_id)
        
        profile.typical_login_hours.add(timestamp.hour)
        profile.last_updated = datetime.now(UTC)
        
        # Keep only last 100 logins
        if len(self.login_history[user_id]) > 100:
            self.login_history[user_id] = self.login_history[user_id][-100:]
    
    def record_data_access(
        self,
        user_id: str,
        timestamp: datetime,
        resource_id: str,
        access_size_gb: float,
    ):
        """Record data access event."""
        profile = self.get_or_create_profile(user_id)
        
        # Track access patterns
        profile.access_patterns[resource_id] = profile.access_patterns.get(resource_id, 0) + 1
        
        # Record in history
        self.access_history[user_id].append((timestamp, resource_id, int(access_size_gb)))
        
        profile.last_updated = datetime.now(UTC)
        
        # Keep only last 500 accesses
        if len(self.access_history[user_id]) > 500:
            self.access_history[user_id] = self.access_history[user_id][-500:]
    
    def get_typical_volume(self, user_id: str, hours: int = 24) -> float:
        """Get typical data access volume in GB per day."""
        if user_id not in self.access_history:
            return 0.0
        
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        total_gb = sum(
            size for ts, _, size in self.access_history[user_id]
            if ts > cutoff
        )
        return total_gb
    
    def get_unusual_patterns(self, user_id: str) -> Dict[str, any]:
        """Get unusual patterns for user."""
        profile = self.profiles.get(user_id)
        if not profile:
            return {}
        
        return {
            "new_ip_addresses": len(profile.typical_ip_addresses),
            "new_devices": len(profile.devices_used),
            "typical_hours": list(profile.typical_login_hours),
            "access_count": sum(profile.access_patterns.values()),
        }


# ============================================================================
# Anomaly Detectors
# ============================================================================

class AnomalyDetector(ABC):
    """Abstract base for anomaly detection."""
    
    @abstractmethod
    def detect(self, context: Dict[str, any]) -> Optional[DetectedAnomaly]:
        """Detect anomaly from context. Returns None if no anomaly."""
        pass


class ImpossibleTravelDetector(AnomalyDetector):
    """Detect geographically impossible travel between logins."""
    
    # Speed of travel in km/hour (max realistic speed ~900 km/h for commercial flight)
    MAX_TRAVEL_SPEED = 900
    
    def detect(self, context: Dict[str, any]) -> Optional[DetectedAnomaly]:
        """
        Detect if user logged in from two locations too close in time
        to be physically possible.
        
        Context: {
            "user_id": str,
            "last_login_location": {"lat": float, "lon": float, "country": str},
            "current_location": {"lat": float, "lon": float, "country": str},
            "time_diff_minutes": float,
            "timestamp": datetime,
        }
        """
        if not all(k in context for k in ["last_login_location", "current_location", "time_diff_minutes"]):
            return None
        
        last_loc = context["last_login_location"]
        curr_loc = context["current_location"]
        time_diff = context["time_diff_minutes"]
        
        # Skip if insufficient data
        if not last_loc or not curr_loc or time_diff < 1:
            return None
        
        # Calculate distance (simplified - use Haversine formula in production)
        distance_km = self._calculate_distance(
            last_loc.get("lat"), last_loc.get("lon"),
            curr_loc.get("lat"), curr_loc.get("lon")
        )
        
        # Check if travel time is impossible
        required_hours = distance_km / self.MAX_TRAVEL_SPEED
        actual_hours = time_diff / 60
        
        if actual_hours < required_hours:
            confidence = min(1.0, (required_hours / actual_hours) ** 0.5)
            
            return DetectedAnomaly(
                anomaly_type=AnomalyType.IMPOSSIBLE_TRAVEL,
                threat_level=ThreatLevel.CRITICAL,
                user_id=context.get("user_id", "unknown"),
                timestamp=context.get("timestamp", datetime.now(UTC)),
                message=f"Impossible travel: {distance_km:.0f}km in {actual_hours:.1f}h",
                metadata={
                    "distance_km": distance_km,
                    "time_hours": actual_hours,
                    "required_hours": required_hours,
                    "from": last_loc,
                    "to": curr_loc,
                },
                confidence_score=confidence,
                recommendations=["Verify user identity", "Review account access logs"],
            )
        
        return None
    
    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates (simplified)."""
        import math
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        R = 6371  # Earth's radius in km
        return R * c


class BruteForceDetector(AnomalyDetector):
    """Detect brute force attack attempts."""
    
    def __init__(self, threshold: int = 5, window_minutes: int = 10):
        self.threshold = threshold
        self.window_minutes = window_minutes
        self.failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
    
    def record_failed_attempt(self, user_id: str, timestamp: datetime):
        """Record failed authentication attempt."""
        self.failed_attempts[user_id].append(timestamp)
        
        # Clean up old attempts
        cutoff = timestamp - timedelta(minutes=self.window_minutes * 10)
        self.failed_attempts[user_id] = [
            t for t in self.failed_attempts[user_id] if t > cutoff
        ]
    
    def detect(self, context: Dict[str, any]) -> Optional[DetectedAnomaly]:
        """
        Detect multiple failed authentication attempts.
        
        Context: {
            "user_id": str,
            "timestamp": datetime,
            "ip_address": str,
        }
        """
        user_id = context.get("user_id")
        timestamp = context.get("timestamp", datetime.now(UTC))
        
        if not user_id:
            return None
        
        # Count failed attempts in window
        cutoff = timestamp - timedelta(minutes=self.window_minutes)
        attempts = [t for t in self.failed_attempts.get(user_id, []) if t > cutoff]
        
        if len(attempts) >= self.threshold:
            confidence = min(1.0, len(attempts) / self.threshold)
            
            return DetectedAnomaly(
                anomaly_type=AnomalyType.BRUTE_FORCE,
                threat_level=ThreatLevel.HIGH,
                user_id=user_id,
                timestamp=timestamp,
                message=f"{len(attempts)} failed authentication attempts in {self.window_minutes} minutes",
                metadata={
                    "failed_attempts": len(attempts),
                    "window_minutes": self.window_minutes,
                    "ip_address": context.get("ip_address"),
                },
                confidence_score=confidence,
                recommendations=[
                    "Block account temporarily",
                    "Require password reset",
                    "Review login attempts",
                    "Check for credential compromise",
                ],
            )
        
        return None


class DataExfiltrationDetector(AnomalyDetector):
    """Detect unusual data access patterns indicating exfiltration."""
    
    def __init__(self, baseline: UserBehaviorBaseline):
        self.baseline = baseline
    
    def detect(self, context: Dict[str, any]) -> Optional[DetectedAnomaly]:
        """
        Detect unusual data access volume or patterns.
        
        Context: {
            "user_id": str,
            "timestamp": datetime,
            "access_size_gb": float,
            "resource_type": str,
        }
        """
        user_id = context.get("user_id")
        access_size = context.get("access_size_gb", 0)
        timestamp = context.get("timestamp", datetime.now(UTC))
        
        if not user_id:
            return None
        
        # Get baseline
        typical_volume = self.baseline.get_typical_volume(user_id)
        
        # Check if this access is unusual
        if typical_volume > 0 and access_size > typical_volume * 5:
            confidence = min(1.0, (access_size / (typical_volume * 5)))
            
            return DetectedAnomaly(
                anomaly_type=AnomalyType.DATA_EXFILTRATION,
                threat_level=ThreatLevel.MEDIUM,
                user_id=user_id,
                timestamp=timestamp,
                message=f"Unusual data access: {access_size:.2f}GB (typical: {typical_volume:.2f}GB/day)",
                metadata={
                    "access_size_gb": access_size,
                    "typical_volume_gb": typical_volume,
                    "resource_type": context.get("resource_type"),
                },
                confidence_score=confidence,
                recommendations=[
                    "Review access request",
                    "Verify with user",
                    "Check destination of data",
                ],
            )
        
        return None


class SuspiciousPatternDetector(AnomalyDetector):
    """Detect suspicious patterns with custom rules."""
    
    def __init__(self):
        self.patterns = [
            {
                "name": "root_access",
                "regex": r"(root|admin|system)",
                "severity": ThreatLevel.CRITICAL,
            },
            {
                "name": "sql_injection",
                "regex": r"(;|\bOR\b|UNION|SELECT|DROP)",
                "severity": ThreatLevel.HIGH,
            },
            {
                "name": "directory_traversal",
                "regex": r"(\.\.\/|\.\.\\)",
                "severity": ThreatLevel.HIGH,
            },
        ]
    
    def detect(self, context: Dict[str, any]) -> Optional[DetectedAnomaly]:
        """
        Detect suspicious patterns in query/command.
        
        Context: {
            "user_id": str,
            "query": str,
            "timestamp": datetime,
        }
        """
        user_id = context.get("user_id")
        query = context.get("query", "")
        timestamp = context.get("timestamp", datetime.now(UTC))
        
        if not query:
            return None
        
        for pattern in self.patterns:
            if re.search(pattern["regex"], query, re.IGNORECASE):
                return DetectedAnomaly(
                    anomaly_type=AnomalyType.SUSPICIOUS_PATTERN,
                    threat_level=pattern["severity"],
                    user_id=user_id,
                    timestamp=timestamp,
                    message=f"Suspicious pattern detected: {pattern['name']}",
                    metadata={
                        "pattern": pattern["name"],
                        "matched_text": query[:100],  # First 100 chars
                    },
                    confidence_score=0.8,
                    recommendations=[
                        "Block operation",
                        "Log query details",
                        "Alert security team",
                    ],
                )
        
        return None


class AnomalyTimeDetector(AnomalyDetector):
    """Detect access at unusual times."""
    
    def __init__(self, baseline: UserBehaviorBaseline):
        self.baseline = baseline
    
    def detect(self, context: Dict[str, any]) -> Optional[DetectedAnomaly]:
        """
        Detect access outside user's typical hours.
        
        Context: {
            "user_id": str,
            "timestamp": datetime,
        }
        """
        user_id = context.get("user_id")
        timestamp = context.get("timestamp", datetime.now(UTC))
        
        if not user_id:
            return None
        
        profile = self.baseline.profiles.get(user_id)
        if not profile or not profile.typical_login_hours:
            return None
        
        if timestamp.hour not in profile.typical_login_hours:
            return DetectedAnomaly(
                anomaly_type=AnomalyType.ANOMALOUS_TIME,
                threat_level=ThreatLevel.LOW,
                user_id=user_id,
                timestamp=timestamp,
                message=f"Login at unusual time: {timestamp.hour:02d}:00 (typical: {sorted(profile.typical_login_hours)})",
                metadata={
                    "login_hour": timestamp.hour,
                    "typical_hours": list(profile.typical_login_hours),
                },
                confidence_score=0.6,
                recommendations=["Monitor account activity"],
            )
        
        return None


class BulkOperationDetector(AnomalyDetector):
    """Detect unusual bulk operations."""
    
    def __init__(self, threshold: int = 1000):
        self.threshold = threshold
    
    def detect(self, context: Dict[str, any]) -> Optional[DetectedAnomaly]:
        """
        Detect bulk data operations.
        
        Context: {
            "user_id": str,
            "operation_type": str,
            "record_count": int,
            "timestamp": datetime,
        }
        """
        user_id = context.get("user_id")
        record_count = context.get("record_count", 0)
        timestamp = context.get("timestamp", datetime.now(UTC))
        
        if record_count > self.threshold:
            return DetectedAnomaly(
                anomaly_type=AnomalyType.BULK_OPERATION,
                threat_level=ThreatLevel.MEDIUM,
                user_id=user_id,
                timestamp=timestamp,
                message=f"Bulk operation: {record_count} records",
                metadata={
                    "record_count": record_count,
                    "operation_type": context.get("operation_type"),
                },
                confidence_score=0.7,
                recommendations=[
                    "Verify operation legitimacy",
                    "Review data retention policies",
                    "Log operation details",
                ],
            )
        
        return None


# ============================================================================
# Anomaly Detection Engine
# ============================================================================

class AnomalyDetectionEngine:
    """Central engine for security anomaly detection."""
    
    def __init__(self):
        self.baseline = UserBehaviorBaseline()
        self.detectors: List[AnomalyDetector] = [
            ImpossibleTravelDetector(),
            BruteForceDetector(),
            DataExfiltrationDetector(self.baseline),
            SuspiciousPatternDetector(),
            AnomalyTimeDetector(self.baseline),
            BulkOperationDetector(),
        ]
        self.detected_anomalies: List[DetectedAnomaly] = []
        self.thresholds: Dict[AnomalyType, AnomalyThreshold] = {}
    
    def record_login(
        self,
        user_id: str,
        timestamp: datetime,
        location: Optional[Dict[str, any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Record login for baseline analysis."""
        self.baseline.record_login(user_id, timestamp, location, ip_address, user_agent)
    
    def record_data_access(
        self,
        user_id: str,
        timestamp: datetime,
        resource_id: str,
        access_size_gb: float,
    ):
        """Record data access for baseline analysis."""
        self.baseline.record_data_access(user_id, timestamp, resource_id, access_size_gb)
    
    def detect_anomalies(self, context: Dict[str, any]) -> List[DetectedAnomaly]:
        """Run all detectors and return detected anomalies."""
        detected = []
        
        for detector in self.detectors:
            anomaly = detector.detect(context)
            if anomaly:
                detected.append(anomaly)
                self.detected_anomalies.append(anomaly)
        
        return detected
    
    def get_recent_anomalies(self, user_id: Optional[str] = None, hours: int = 24) -> List[DetectedAnomaly]:
        """Get anomalies from recent time period."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        
        result = [a for a in self.detected_anomalies if a.timestamp > cutoff]
        
        if user_id:
            result = [a for a in result if a.user_id == user_id]
        
        return result
    
    def get_high_risk_users(self, threshold: int = 5, hours: int = 24) -> List[Tuple[str, int]]:
        """Get users with anomalies above threshold in recent period."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        
        anomaly_counts: Dict[str, int] = defaultdict(int)
        for a in self.detected_anomalies:
            if a.timestamp > cutoff and a.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
                anomaly_counts[a.user_id] += 1
        
        return [(u, c) for u, c in anomaly_counts.items() if c >= threshold]


# Singleton instance
_engine = None

def get_anomaly_detection_engine() -> AnomalyDetectionEngine:
    """Get singleton anomaly detection engine."""
    global _engine
    if _engine is None:
        _engine = AnomalyDetectionEngine()
    return _engine
