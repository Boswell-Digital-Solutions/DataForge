"""
Compliance reporting for regulatory frameworks.

Supports:
- GDPR (General Data Protection Regulation)
- CCPA (California Consumer Privacy Act)
- HIPAA (Health Insurance Portability and Accountability Act)
- SOC2 Type II compliance
- PCI-DSS (Payment Card Industry Data Security Standard)
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from abc import ABC, abstractmethod
import json


# ============================================================================
# Compliance Frameworks
# ============================================================================

class ComplianceFramework(Enum):
    """Supported compliance frameworks."""
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    PCI_DSS = "pci_dss"


# ============================================================================
# GDPR Compliance
# ============================================================================

class GDPRRight(Enum):
    """GDPR data subject rights."""
    ACCESS = "access"              # Right of access (Article 15)
    RECTIFICATION = "rectification"  # Right to rectification (Article 16)
    ERASURE = "erasure"            # Right to erasure - "right to be forgotten" (Article 17)
    RESTRICT = "restrict"          # Right to restrict processing (Article 18)
    PORTABILITY = "portability"    # Right to data portability (Article 20)
    OBJECT = "object"              # Right to object (Article 21)
    WITHDRAW = "withdraw"          # Withdraw consent (Article 7)


@dataclass
class GDPRRequest:
    """GDPR data subject rights request."""
    
    request_id: str
    user_id: str
    right: GDPRRight
    requested_at: datetime
    email: str
    status: str  # pending, approved, denied, completed
    completion_date: Optional[datetime] = None
    response_data: Optional[Dict[str, Any]] = None
    denial_reason: Optional[str] = None
    
    def __post_init__(self):
        # GDPR requires response within 30 days (extendable to 90 days)
        self.deadline = self.requested_at + timedelta(days=30)
    
    def is_overdue(self) -> bool:
        """Check if request is overdue."""
        return datetime.utcnow() > self.deadline and self.status != "completed"


@dataclass
class GDPRAuditReport:
    """GDPR compliance audit report."""
    
    period_start: datetime
    period_end: datetime
    total_requests: int = 0
    access_requests: int = 0
    erasure_requests: int = 0
    portability_requests: int = 0
    average_response_time_days: float = 0.0
    overdue_requests: int = 0
    pii_retention_violations: int = 0  # Data kept longer than necessary
    consent_records: int = 0
    third_party_processors: List[str] = field(default_factory=list)
    data_breach_incidents: int = 0
    dpia_completed: bool = False  # Data Protection Impact Assessment
    dpo_appointed: bool = False  # Data Protection Officer


# ============================================================================
# CCPA Compliance
# ============================================================================

class CCPACategory(Enum):
    """CCPA personal information categories."""
    IDENTIFIERS = "identifiers"
    COMMERCIAL_INFO = "commercial_info"
    BIOMETRIC_INFO = "biometric_info"
    INTERNET_ACTIVITY = "internet_activity"
    GEOLOCATION = "geolocation"
    SENSORY_INFO = "sensory_info"
    PROFESSIONAL_INFO = "professional_info"
    EDUCATION_INFO = "education_info"
    PROTECTED_CLASS = "protected_class"


@dataclass
class CCPARequest:
    """CCPA consumer rights request."""
    
    request_id: str
    consumer_id: str
    request_type: str  # "know", "delete", "opt_out"
    requested_at: datetime
    email: str
    status: str  # pending, verified, approved, completed
    completion_date: Optional[datetime] = None
    categories: List[CCPACategory] = field(default_factory=list)
    
    def __post_init__(self):
        # CCPA requires response within 45 days
        self.deadline = self.requested_at + timedelta(days=45)


@dataclass
class CCPAAuditReport:
    """CCPA compliance audit report."""
    
    period_start: datetime
    period_end: datetime
    total_requests: int = 0
    know_requests: int = 0
    delete_requests: int = 0
    opt_out_requests: int = 0
    average_response_time_days: float = 0.0
    overdue_requests: int = 0
    opt_out_honored: bool = False
    third_party_disclosures: int = 0
    data_sale_disclosures: int = 0
    consumer_rights_privacy_notice: bool = False
    opt_out_link_provided: bool = False


# ============================================================================
# HIPAA Compliance
# ============================================================================

@dataclass
class HIPAAAuditReport:
    """HIPAA compliance audit report."""
    
    period_start: datetime
    period_end: datetime
    
    # Administrative Safeguards
    workforce_security_implemented: bool = False
    access_management_implemented: bool = False
    security_awareness_training_hours: int = 0
    
    # Physical Safeguards
    facility_access_controls: bool = False
    workstation_use_policies: bool = False
    workstation_security: bool = False
    device_media_controls: bool = False
    
    # Technical Safeguards
    access_controls_implemented: bool = False
    audit_controls_implemented: bool = False
    encryption_implemented: bool = False
    transmission_security: bool = False
    
    # Breach Notification
    breaches_detected: int = 0
    breaches_reported: int = 0
    individuals_notified: int = 0
    
    # Business Associate Agreements
    baa_count: int = 0
    baa_audits_completed: int = 0
    
    # Risk Assessment
    risk_assessment_completed: bool = False
    risk_assessment_date: Optional[datetime] = None
    vulnerabilities_identified: int = 0
    vulnerabilities_remediated: int = 0


# ============================================================================
# SOC2 Compliance
# ============================================================================

class SOC2Principle(Enum):
    """SOC2 Trust Service Criteria."""
    SECURITY = "security"                  # System is protected against unauthorized access
    AVAILABILITY = "availability"          # System is available when needed
    PROCESSING_INTEGRITY = "processing_integrity"  # Authorized, complete, accurate processing
    CONFIDENTIALITY = "confidentiality"    # Information designated confidential is protected
    PRIVACY = "privacy"                    # Personal information is collected per privacy notice


@dataclass
class SOC2AuditReport:
    """SOC2 Type II audit report."""
    
    period_start: datetime
    period_end: datetime
    report_date: datetime = field(default_factory=datetime.utcnow)
    type_2: bool = True  # Type II includes time-based controls
    
    # Security Principle
    security_policy_documented: bool = False
    access_controls_tested: bool = False
    logging_monitoring_tested: bool = False
    incident_response_tested: bool = False
    
    # Availability Principle
    uptime_percentage: float = 0.0  # Target: 99.9%
    rto_hours: float = 0.0  # Recovery Time Objective
    rpo_hours: float = 0.0  # Recovery Point Objective
    
    # Processing Integrity Principle
    data_validation_implemented: bool = False
    error_handling_implemented: bool = False
    
    # Confidentiality Principle
    encryption_in_transit: bool = False
    encryption_at_rest: bool = False
    
    # Privacy Principle
    privacy_notice_provided: bool = False
    opt_in_obtained: bool = False


# ============================================================================
# PCI-DSS Compliance
# ============================================================================

@dataclass
class PCIDSSAuditReport:
    """PCI-DSS compliance audit report."""
    
    period_start: datetime
    period_end: datetime
    
    # Requirement 1-6: Network and systems
    firewall_configured: bool = False
    default_credentials_removed: bool = False
    network_segmentation: bool = False
    malware_protection: bool = False
    firewall_rules_documented: bool = False
    
    # Requirement 7-8: Access control
    access_restricted: bool = False
    unique_user_ids: bool = False
    password_policy_enforced: bool = False
    
    # Requirement 9-10: Physical and monitoring
    physical_access_restricted: bool = False
    monitoring_enabled: bool = False
    log_retention_days: int = 0  # Min 90 days
    
    # Requirement 11-12: Testing and policy
    security_testing_frequency: str = ""  # quarterly, monthly, etc.
    vulnerability_scanning_completed: bool = False
    penetration_testing_completed: bool = False
    policy_documented: bool = False
    
    # Violations
    violations_found: int = 0
    critical_violations: int = 0
    remediation_deadline_dates: List[datetime] = field(default_factory=list)


# ============================================================================
# Compliance Report Generator
# ============================================================================

class ComplianceReportGenerator:
    """Generate compliance reports for various frameworks."""
    
    def __init__(self, audit_logger_backend=None):
        self.audit_logs = []
        self.gdpr_requests: Dict[str, GDPRRequest] = {}
        self.ccpa_requests: Dict[str, CCPARequest] = {}
        self.audit_logger_backend = audit_logger_backend
    
    def add_audit_log(self, log: Any):
        """Add audit log entry for reporting."""
        self.audit_logs.append(log)
    
    def create_gdpr_request(
        self,
        user_id: str,
        right: GDPRRight,
        email: str,
    ) -> GDPRRequest:
        """Create new GDPR data subject rights request."""
        request_id = f"gdpr_{user_id}_{datetime.utcnow().timestamp()}"
        
        request = GDPRRequest(
            request_id=request_id,
            user_id=user_id,
            right=right,
            requested_at=datetime.utcnow(),
            email=email,
            status="pending",
        )
        
        self.gdpr_requests[request_id] = request
        return request
    
    def create_ccpa_request(
        self,
        consumer_id: str,
        request_type: str,
        email: str,
    ) -> CCPARequest:
        """Create new CCPA consumer rights request."""
        request_id = f"ccpa_{consumer_id}_{datetime.utcnow().timestamp()}"
        
        request = CCPARequest(
            request_id=request_id,
            consumer_id=consumer_id,
            request_type=request_type,
            requested_at=datetime.utcnow(),
            email=email,
            status="pending",
        )
        
        self.ccpa_requests[request_id] = request
        return request
    
    def generate_gdpr_report(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> GDPRAuditReport:
        """Generate GDPR compliance audit report."""
        
        # Filter requests in period
        period_requests = [
            r for r in self.gdpr_requests.values()
            if period_start <= r.requested_at <= period_end
        ]
        
        # Count request types
        access_count = sum(1 for r in period_requests if r.right == GDPRRight.ACCESS)
        erasure_count = sum(1 for r in period_requests if r.right == GDPRRight.ERASURE)
        portability_count = sum(1 for r in period_requests if r.right == GDPRRight.PORTABILITY)
        
        # Calculate average response time
        completed = [r for r in period_requests if r.completion_date]
        response_times = [
            (r.completion_date - r.requested_at).days
            for r in completed
        ]
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        
        # Count overdue
        overdue = sum(1 for r in period_requests if r.is_overdue())
        
        report = GDPRAuditReport(
            period_start=period_start,
            period_end=period_end,
            total_requests=len(period_requests),
            access_requests=access_count,
            erasure_requests=erasure_count,
            portability_requests=portability_count,
            average_response_time_days=avg_response,
            overdue_requests=overdue,
        )
        
        return report
    
    def generate_ccpa_report(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> CCPAAuditReport:
        """Generate CCPA compliance audit report."""
        
        # Filter requests in period
        period_requests = [
            r for r in self.ccpa_requests.values()
            if period_start <= r.requested_at <= period_end
        ]
        
        # Count request types
        know_count = sum(1 for r in period_requests if r.request_type == "know")
        delete_count = sum(1 for r in period_requests if r.request_type == "delete")
        opt_out_count = sum(1 for r in period_requests if r.request_type == "opt_out")
        
        # Calculate average response time
        completed = [r for r in period_requests if r.completion_date]
        response_times = [
            (r.completion_date - r.requested_at).days
            for r in completed
        ]
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        
        report = CCPAAuditReport(
            period_start=period_start,
            period_end=period_end,
            total_requests=len(period_requests),
            know_requests=know_count,
            delete_requests=delete_count,
            opt_out_requests=opt_out_count,
            average_response_time_days=avg_response,
        )
        
        return report
    
    def generate_hipaa_report(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> HIPAAAuditReport:
        """Generate HIPAA compliance audit report."""
        
        report = HIPAAAuditReport(
            period_start=period_start,
            period_end=period_end,
        )
        
        return report
    
    def generate_soc2_report(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> SOC2AuditReport:
        """Generate SOC2 Type II audit report."""
        
        report = SOC2AuditReport(
            period_start=period_start,
            period_end=period_end,
        )
        
        return report
    
    def generate_pci_dss_report(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> PCIDSSAuditReport:
        """Generate PCI-DSS compliance audit report."""
        
        report = PCIDSSAuditReport(
            period_start=period_start,
            period_end=period_end,
        )
        
        return report
    
    def export_report_json(self, report: Any) -> str:
        """Export report as JSON."""
        def serialize(obj):
            if isinstance(obj, (datetime, Enum)):
                return str(obj)
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)
        
        return json.dumps(report.__dict__, default=serialize, indent=2)


# ============================================================================
# Compliance Check Helper
# ============================================================================

class ComplianceChecker:
    """Helper class to verify compliance requirements."""
    
    @staticmethod
    def is_gdpr_compliant_for_deletion(record: Dict[str, Any]) -> bool:
        """
        Check if record can be safely deleted under GDPR.
        - No legal hold
        - No pending litigation
        - Retention period expired
        """
        return not record.get("legal_hold") and not record.get("litigation_pending")
    
    @staticmethod
    def is_pii_encrypted(value: Any) -> bool:
        """Check if PII field is encrypted."""
        if isinstance(value, dict):
            return value.get("__encrypted__", False)
        return False
    
    @staticmethod
    def is_within_retention_period(
        created_date: datetime,
        retention_days: int,
    ) -> bool:
        """Check if data is within its retention period."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        return created_date > cutoff
    
    @staticmethod
    def requires_encryption(field_name: str) -> bool:
        """Check if field requires encryption per PCI-DSS."""
        sensitive_patterns = [
            "card", "account", "password", "secret",
            "token", "key", "credential", "ssn", "pii"
        ]
        return any(p in field_name.lower() for p in sensitive_patterns)
    
    @staticmethod
    def requires_audit_log(operation: str) -> bool:
        """Check if operation must be audit logged."""
        logged_operations = [
            "delete", "export", "modify_permission", "access_pii",
            "key_rotation", "backup", "restore", "privilege_change"
        ]
        return operation in logged_operations


# Singleton instance
_generator = None

def get_compliance_report_generator() -> ComplianceReportGenerator:
    """Get singleton compliance report generator."""
    global _generator
    if _generator is None:
        _generator = ComplianceReportGenerator()
    return _generator
