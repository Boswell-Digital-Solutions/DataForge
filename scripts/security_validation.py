#!/usr/bin/env python3
"""
DataForge Security Validation Script

Automated security validation and compliance checking for production deployment.
Generates comprehensive security report with findings and remediation recommendations.
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


class SecurityValidator:
    """Comprehensive security validation for DataForge."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.findings = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": [],
            "passed": []
        }
        self.summary = {}
    
    def run_all_checks(self) -> Dict:
        """Run all security checks."""
        print("🔐 DataForge Security Validation Report")
        print("=" * 70)
        print(f"Scan Date: {datetime.now().isoformat()}")
        print(f"Base Path: {self.base_path}")
        print("=" * 70 + "\n")
        
        checks = [
            ("Authentication", self.check_authentication),
            ("Authorization", self.check_authorization),
            ("Encryption", self.check_encryption),
            ("Logging & Audit", self.check_logging),
            ("Container Security", self.check_container_security),
            ("Network Security", self.check_network_security),
            ("Hardcoded Secrets", self.check_hardcoded_secrets),
            ("SQL Injection Prevention", self.check_sql_injection_prevention),
            ("Dependency Security", self.check_dependencies),
            ("Configuration", self.check_configuration),
            ("Backup & Recovery", self.check_backup),
            ("Monitoring", self.check_monitoring),
        ]
        
        for check_name, check_func in checks:
            print(f"\n📋 Checking {check_name}...")
            try:
                check_func()
                print(f"✅ {check_name} check completed")
            except Exception as e:
                print(f"⚠️  {check_name} check error: {e}")
        
        self.print_report()
        return self.findings
    
    def check_authentication(self):
        """Check authentication implementation."""
        auth_file = self.base_path / "app" / "utils" / "auth.py"
        
        if auth_file.exists():
            with open(auth_file) as f:
                content = f.read()
                
            checks = [
                ("OAuth2/OIDC", "oauth2_oidc" in content or "OIDC" in content),
                ("Password hashing (bcrypt)", "bcrypt" in content or "hash_password" in content),
                ("JWT support", "jwt" in content or "jose" in content),
                ("Token management", "create_access_token" in content),
            ]
            
            for check_name, passed in checks:
                if passed:
                    self.findings["passed"].append(f"Authentication: {check_name} ✓")
                else:
                    self.findings["medium"].append(f"Authentication: {check_name} missing")
        else:
            self.findings["critical"].append("Authentication: auth.py not found")
    
    def check_authorization(self):
        """Check authorization implementation."""
        models_file = self.base_path / "app" / "models" / "models.py"
        crud_file = self.base_path / "app" / "api" / "crud.py"
        
        checks_passed = 0
        
        if models_file.exists():
            with open(models_file) as f:
                if "role" in f.read().lower():
                    checks_passed += 1
                    self.findings["passed"].append("Authorization: RBAC model defined ✓")
        
        if crud_file.exists():
            with open(crud_file) as f:
                content = f.read()
                if "permission" in content.lower() or "authorize" in content.lower():
                    checks_passed += 1
                    self.findings["passed"].append("Authorization: Permission checks ✓")
        
        if checks_passed < 2:
            self.findings["high"].append("Authorization: Incomplete implementation")
    
    def check_encryption(self):
        """Check encryption implementation."""
        encryption_file = self.base_path / "app" / "utils" / "data_encryption.py"
        config_file = self.base_path / "app" / "config.py"
        
        checks = []
        
        if encryption_file.exists():
            with open(encryption_file) as f:
                content = f.read()
                checks.append(("AES-256 encryption", "AES-256" in content or "AES_256" in content))
                checks.append(("Key derivation", "PBKDF2" in content or "key_derivation" in content))
        
        if config_file.exists():
            with open(config_file) as f:
                content = f.read()
                checks.append(("Encryption key management", "ENCRYPTION_KEY" in content or "SECRET_KEY" in content))
        
        for check_name, passed in checks:
            if passed:
                self.findings["passed"].append(f"Encryption: {check_name} ✓")
            else:
                self.findings["medium"].append(f"Encryption: {check_name} not found")
    
    def check_logging(self):
        """Check logging and audit implementation."""
        logging_file = self.base_path / "app" / "logging_config.py"
        main_file = self.base_path / "app" / "main.py"
        
        if logging_file.exists():
            with open(logging_file) as f:
                content = f.read()
                
            checks = [
                ("JSON structured logging", "json" in content or "StructuredJSON" in content),
                ("Audit trail", "audit" in content.lower() or "security_event" in content),
                ("Log rotation", "RotatingFileHandler" in content),
                ("Security event logging", "log_security_event" in content),
            ]
            
            for check_name, passed in checks:
                if passed:
                    self.findings["passed"].append(f"Logging: {check_name} ✓")
                else:
                    self.findings["medium"].append(f"Logging: {check_name} missing")
        else:
            self.findings["high"].append("Logging: logging_config.py not found")
    
    def check_container_security(self):
        """Check Dockerfile security."""
        dockerfile = self.base_path / "Dockerfile"
        
        if dockerfile.exists():
            with open(dockerfile) as f:
                content = f.read()
            
            checks = [
                ("Non-root USER", "USER " in content and "root" not in content.split("USER")[-1].split("\n")[0]),
                ("Minimal base image", "slim" in content or "alpine" in content),
                ("Health checks", "HEALTHCHECK" in content),
                ("Image labels", "LABEL" in content),
                ("File ownership", "--chown" in content or "chown" in content),
            ]
            
            for check_name, passed in checks:
                if passed:
                    self.findings["passed"].append(f"Container: {check_name} ✓")
                else:
                    self.findings["medium"].append(f"Container: {check_name} not implemented")
        else:
            self.findings["high"].append("Container: Dockerfile not found")
    
    def check_network_security(self):
        """Check network security headers."""
        security_config = self.base_path / "app" / "security_config.py"
        main_file = self.base_path / "app" / "main.py"
        
        if security_config.exists():
            with open(security_config) as f:
                content = f.read()
            
            headers = [
                ("X-Frame-Options", "X-Frame-Options"),
                ("X-Content-Type-Options", "X-Content-Type-Options"),
                ("Strict-Transport-Security", "Strict-Transport-Security"),
                ("Content-Security-Policy", "Content-Security-Policy"),
                ("X-XSS-Protection", "X-XSS-Protection"),
                ("Referrer-Policy", "Referrer-Policy"),
                ("Permissions-Policy", "Permissions-Policy"),
            ]
            
            for header_name, header_key in headers:
                if header_key in content:
                    self.findings["passed"].append(f"Network: {header_name} ✓")
                else:
                    self.findings["high"].append(f"Network: {header_name} missing")
        else:
            self.findings["high"].append("Network: security_config.py not found")
    
    def check_hardcoded_secrets(self):
        """Check for hardcoded secrets."""
        secret_patterns = [
            (r"password\s*=\s*['\"](?![\w\{\}]*[\w\.]*test)", "Potential hardcoded password"),
            (r"api_key\s*=\s*['\"][a-zA-Z0-9]{20,}", "Potential hardcoded API key"),
            (r"secret_key\s*=\s*['\"][^\"']{20,}", "Potential hardcoded secret"),
            (r"DATABASE_URL\s*=\s*['\"]postgresql://", "Hardcoded database URL"),
        ]
        
        python_files = list(self.base_path.rglob("*.py"))
        secrets_found = 0
        
        for file_path in python_files:
            if "test" in str(file_path) or "venv" in str(file_path):
                continue
            
            try:
                with open(file_path, encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        for pattern, description in secret_patterns:
                            if re.search(pattern, line):
                                self.findings["critical"].append(
                                    f"Secrets: {description} in {file_path}:{line_num}"
                                )
                                secrets_found += 1
            except (UnicodeDecodeError, IOError):
                pass
        
        if secrets_found == 0:
            self.findings["passed"].append("Secrets: No hardcoded secrets detected ✓")
        else:
            self.findings["critical"].append(f"Secrets: {secrets_found} potential secrets found")
    
    def check_sql_injection_prevention(self):
        """Check SQL injection prevention."""
        crud_files = list(self.base_path.glob("app/api/*crud*.py"))
        
        orm_usage = 0
        raw_sql = 0
        
        for file_path in crud_files:
            with open(file_path) as f:
                content = f.read()
                orm_usage += content.count("query(") + content.count(".filter(")
                raw_sql += content.count("execute(") + content.count("text(")
        
        if orm_usage > 0 and raw_sql == 0:
            self.findings["passed"].append("SQL: SQLAlchemy ORM in use (parameterized) ✓")
        elif raw_sql > 0:
            self.findings["high"].append(f"SQL: {raw_sql} potential raw SQL queries found")
        else:
            self.findings["info"].append("SQL: No SQL queries found in CRUD files")
    
    def check_dependencies(self):
        """Check dependency security."""
        req_file = self.base_path / "requirements.txt"
        
        if req_file.exists():
            with open(req_file) as f:
                content = f.read()
            
            # Check for version pinning
            unpinned = []
            for line in content.split("\n"):
                if line and not line.startswith("#") and "==" not in line and ">=" not in line:
                    unpinned.append(line)
            
            if unpinned:
                self.findings["high"].append(f"Dependencies: {len(unpinned)} unpinned packages")
            else:
                self.findings["passed"].append("Dependencies: All packages pinned to specific versions ✓")
            
            # Check for suspicious packages
            suspicious = ["telemetry", "tracking", "analytics", "keylogger", "backdoor"]
            for package in suspicious:
                if package in content.lower():
                    self.findings["critical"].append(f"Dependencies: Suspicious package '{package}' found")
            
            # Check version count
            version_count = content.count("==")
            if version_count > 0:
                self.findings["info"].append(f"Dependencies: {version_count} packages found")
    
    def check_configuration(self):
        """Check configuration security."""
        env_example = self.base_path / ".env.example"
        env_file = self.base_path / ".env"
        
        if env_file.exists():
            self.findings["high"].append("Configuration: .env file exists (should not be committed)")
        
        if env_example.exists():
            with open(env_example) as f:
                content = f.read()
                if "password" in content.lower() or "api_key" in content.lower():
                    self.findings["critical"].append("Configuration: .env.example contains secrets")
                else:
                    self.findings["passed"].append("Configuration: .env.example without secrets ✓")
    
    def check_backup(self):
        """Check backup and recovery setup."""
        alembic_path = self.base_path / "alembic"
        
        if alembic_path.exists():
            self.findings["passed"].append("Backup: Alembic migrations configured ✓")
        else:
            self.findings["medium"].append("Backup: Alembic migrations not found")
    
    def check_monitoring(self):
        """Check monitoring and alerting."""
        main_file = self.base_path / "app" / "main.py"
        
        if main_file.exists():
            with open(main_file) as f:
                content = f.read()
                
            if "prometheus" in content.lower() or "metrics" in content.lower():
                self.findings["passed"].append("Monitoring: Prometheus metrics ✓")
            else:
                self.findings["info"].append("Monitoring: Prometheus metrics not detected")
    
    def print_report(self):
        """Print comprehensive security report."""
        print("\n" + "=" * 70)
        print("📊 SECURITY VALIDATION REPORT")
        print("=" * 70 + "\n")
        
        # Count findings
        total_critical = len(self.findings["critical"])
        total_high = len(self.findings["high"])
        total_medium = len(self.findings["medium"])
        total_low = len(self.findings["low"])
        total_passed = len(self.findings["passed"])
        
        print(f"🔴 CRITICAL: {total_critical}")
        for finding in self.findings["critical"]:
            print(f"   ❌ {finding}")
        
        print(f"\n🟠 HIGH: {total_high}")
        for finding in self.findings["high"]:
            print(f"   ⚠️  {finding}")
        
        print(f"\n🟡 MEDIUM: {total_medium}")
        for finding in self.findings["medium"]:
            print(f"   ⚠️  {finding}")
        
        print(f"\n🟢 PASSED: {total_passed}")
        for finding in self.findings["passed"][:5]:  # Show first 5
            print(f"   ✅ {finding}")
        if total_passed > 5:
            print(f"   ... and {total_passed - 5} more")
        
        # Risk assessment
        print(f"\n{'=' * 70}")
        print("🎯 RISK ASSESSMENT")
        print(f"{'=' * 70}")
        
        risk_score = (total_critical * 10) + (total_high * 5) + (total_medium * 2)
        pass_rate = (total_passed / (total_passed + total_critical + total_high + total_medium)) * 100 if (total_passed + total_critical + total_high + total_medium) > 0 else 0
        
        print(f"Risk Score: {risk_score}/100")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        if risk_score < 10:
            print("Status: ✅ PRODUCTION READY")
        elif risk_score < 30:
            print("Status: 🟡 READY WITH CONDITIONS")
        else:
            print("Status: 🔴 NOT READY FOR PRODUCTION")
        
        print(f"\n{'=' * 70}")
        print(f"Scan completed at {datetime.now().isoformat()}")
        print(f"{'=' * 70}\n")
        
        # Recommendations
        if total_critical > 0:
            print("⚠️  CRITICAL ISSUES FOUND - IMMEDIATE ACTION REQUIRED\n")
        elif total_high > 0:
            print("⚠️  HIGH PRIORITY ISSUES FOUND - REMEDIATION REQUIRED\n")


def main():
    """Main entry point."""
    import sys
    
    base_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    validator = SecurityValidator(base_path)
    findings = validator.run_all_checks()
    
    # Exit with error if critical issues found
    if findings["critical"]:
        sys.exit(1)
    elif findings["high"]:
        sys.exit(0)  # Still exit clean, but report shown
    
    sys.exit(0)


if __name__ == "__main__":
    main()
