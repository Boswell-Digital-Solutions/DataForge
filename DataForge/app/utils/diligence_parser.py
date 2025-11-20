"""
Due Diligence Dashboard - AI Report Parser

Parses AI-generated markdown reports into structured data.
Supports reports from Claude, ChatGPT, Augment, Cursor, etc.
"""

import re
from typing import Dict, List, Any, Optional
from app.models.diligence_schemas import (
    ParsedAIReport,
    OverallRatingEnum,
    FindingSeverityEnum,
    FindingStatusEnum
)


def parse_ai_report(report_text: str) -> ParsedAIReport:
    """
    Parse an AI-generated due diligence report into structured data.

    Expected markdown format:
    # Summary
    ...

    # Code Quality: 4/5
    ...

    # Security: 3/5
    ...

    # Strengths
    - Strength 1
    - Strength 2

    # Risks
    - Risk 1
    - Risk 2

    # Findings
    ## High Severity
    - Finding 1
    - Finding 2

    # Recommendation
    ...

    # Overall Rating: Green
    """
    parsed = ParsedAIReport()

    # Extract summary
    summary_match = re.search(
        r'#+\s*Summary\s*\n+(.*?)(?=\n#+|\Z)',
        report_text,
        re.DOTALL | re.IGNORECASE
    )
    if summary_match:
        parsed.summary = summary_match.group(1).strip()

    # Extract scores (looking for patterns like "Code Quality: 4/5" or "Code Quality Score: 4")
    scores = {
        'code_quality_score': r'code\s+quality(?:\s+score)?:?\s*(\d+(?:\.\d+)?)',
        'security_score': r'security(?:\s+score)?:?\s*(\d+(?:\.\d+)?)',
        'architecture_score': r'architecture(?:\s+score)?:?\s*(\d+(?:\.\d+)?)',
        'operations_score': r'operations?(?:\s+score)?:?\s*(\d+(?:\.\d+)?)',
        'documentation_score': r'documentation(?:\s+score)?:?\s*(\d+(?:\.\d+)?)'
    }

    for field, pattern in scores.items():
        match = re.search(pattern, report_text, re.IGNORECASE)
        if match:
            score_str = match.group(1)
            score = float(score_str)
            # Normalize to 1-5 scale if needed
            if score > 5:
                score = score / 20  # Assume 0-100 scale
            setattr(parsed, field, min(5.0, max(1.0, score)))

    # Extract strengths (bulleted list)
    strengths_match = re.search(
        r'#+\s*Strengths?\s*\n+((?:[-*]\s+.+\n?)+)',
        report_text,
        re.IGNORECASE
    )
    if strengths_match:
        strengths_text = strengths_match.group(1)
        parsed.strengths = _extract_bullet_points(strengths_text)

    # Extract risks (bulleted list)
    risks_match = re.search(
        r'#+\s*Risks?\s*\n+((?:[-*]\s+.+\n?)+)',
        report_text,
        re.IGNORECASE
    )
    if risks_match:
        risks_text = risks_match.group(1)
        parsed.risks = _extract_bullet_points(risks_text)

    # Extract recommendation
    recommendation_match = re.search(
        r'#+\s*Recommendation\s*\n+(.*?)(?=\n#+|\Z)',
        report_text,
        re.DOTALL | re.IGNORECASE
    )
    if recommendation_match:
        parsed.recommendation = recommendation_match.group(1).strip()

    # Extract overall rating
    rating_match = re.search(
        r'(?:overall\s+rating|rating):?\s*(green|yellow|red)',
        report_text,
        re.IGNORECASE
    )
    if rating_match:
        rating_str = rating_match.group(1).lower()
        parsed.overall_rating = OverallRatingEnum(rating_str)
    else:
        # Infer rating from average score
        parsed.overall_rating = _infer_rating_from_scores(parsed)

    # Extract findings
    parsed.findings = _extract_findings(report_text)

    return parsed


def _extract_bullet_points(text: str) -> List[str]:
    """Extract bullet points from markdown text"""
    lines = text.strip().split('\n')
    points = []
    for line in lines:
        # Remove leading bullet/dash and whitespace
        cleaned = re.sub(r'^[-*•]\s*', '', line.strip())
        if cleaned:
            points.append(cleaned)
    return points


def _extract_findings(report_text: str) -> List[Dict[str, Any]]:
    """
    Extract findings from the report.

    Expected format:
    # Findings
    ## High Severity
    - Finding 1: Description
    - Finding 2: Description

    ## Medium Severity
    - Finding 3: Description
    """
    findings = []

    # Look for Findings section
    findings_match = re.search(
        r'#+\s*Findings?\s*\n+(.*?)(?=\n#(?!#)|\Z)',
        report_text,
        re.DOTALL | re.IGNORECASE
    )

    if not findings_match:
        return findings

    findings_text = findings_match.group(1)

    # Extract by severity sections
    severity_patterns = {
        FindingSeverityEnum.HIGH: r'##\s*(?:high|critical)(?:\s+severity)?\s*\n+((?:[-*]\s+.+\n?)+)',
        FindingSeverityEnum.MEDIUM: r'##\s*medium(?:\s+severity)?\s*\n+((?:[-*]\s+.+\n?)+)',
        FindingSeverityEnum.LOW: r'##\s*low(?:\s+severity)?\s*\n+((?:[-*]\s+.+\n?)+)'
    }

    for severity, pattern in severity_patterns.items():
        match = re.search(pattern, findings_text, re.IGNORECASE)
        if match:
            items_text = match.group(1)
            items = _extract_bullet_points(items_text)

            for item in items:
                # Try to split title and description
                if ':' in item:
                    parts = item.split(':', 1)
                    title = parts[0].strip()
                    description = parts[1].strip()
                else:
                    title = item[:100] + ('...' if len(item) > 100 else '')
                    description = item

                finding = {
                    'title': title,
                    'description': description,
                    'severity': severity.value,
                    'status': FindingStatusEnum.OPEN.value,
                    'category': _infer_category(title + ' ' + description)
                }
                findings.append(finding)

    # If no severity sections found, try to extract all findings at once
    if not findings:
        all_findings_match = re.search(
            r'#+\s*Findings?\s*\n+((?:[-*]\s+.+\n?)+)',
            report_text,
            re.IGNORECASE
        )
        if all_findings_match:
            items_text = all_findings_match.group(1)
            items = _extract_bullet_points(items_text)

            for item in items:
                # Infer severity from keywords
                severity = _infer_severity(item)

                if ':' in item:
                    parts = item.split(':', 1)
                    title = parts[0].strip()
                    description = parts[1].strip()
                else:
                    title = item[:100] + ('...' if len(item) > 100 else '')
                    description = item

                finding = {
                    'title': title,
                    'description': description,
                    'severity': severity.value,
                    'status': FindingStatusEnum.OPEN.value,
                    'category': _infer_category(title + ' ' + description)
                }
                findings.append(finding)

    return findings


def _infer_severity(text: str) -> FindingSeverityEnum:
    """Infer severity from keywords in text"""
    text_lower = text.lower()

    high_keywords = [
        'critical', 'severe', 'dangerous', 'vulnerability', 'security breach',
        'sql injection', 'xss', 'csrf', 'remote code execution', 'authentication bypass'
    ]
    medium_keywords = [
        'warning', 'concern', 'issue', 'problem', 'bug', 'error handling',
        'validation', 'configuration'
    ]

    for keyword in high_keywords:
        if keyword in text_lower:
            return FindingSeverityEnum.HIGH

    for keyword in medium_keywords:
        if keyword in text_lower:
            return FindingSeverityEnum.MEDIUM

    return FindingSeverityEnum.LOW


def _infer_category(text: str) -> Optional[str]:
    """Infer category from keywords in text"""
    text_lower = text.lower()

    categories = {
        'security': ['security', 'vulnerability', 'authentication', 'authorization', 'encryption', 'xss', 'sql injection', 'csrf'],
        'code_quality': ['code quality', 'maintainability', 'complexity', 'duplication', 'technical debt', 'refactor'],
        'architecture': ['architecture', 'design', 'pattern', 'structure', 'coupling', 'cohesion'],
        'performance': ['performance', 'optimization', 'slow', 'memory', 'cpu', 'latency'],
        'documentation': ['documentation', 'comments', 'readme', 'docs', 'undocumented'],
        'testing': ['test', 'testing', 'coverage', 'unit test', 'integration test'],
        'operations': ['deployment', 'infrastructure', 'devops', 'monitoring', 'logging']
    }

    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category

    return None


def _infer_rating_from_scores(parsed: ParsedAIReport) -> OverallRatingEnum:
    """Infer overall rating from average of scores"""
    scores = [
        parsed.code_quality_score,
        parsed.security_score,
        parsed.architecture_score,
        parsed.operations_score,
        parsed.documentation_score
    ]

    # Filter out None values
    valid_scores = [s for s in scores if s is not None]

    if not valid_scores:
        return OverallRatingEnum.YELLOW  # Default to yellow if no scores

    avg_score = sum(valid_scores) / len(valid_scores)

    if avg_score >= 4.0:
        return OverallRatingEnum.GREEN
    elif avg_score >= 2.5:
        return OverallRatingEnum.YELLOW
    else:
        return OverallRatingEnum.RED


def create_sample_report() -> str:
    """
    Generate a sample AI report for testing.
    """
    return """
# Due Diligence Report

## Summary
This is a Python-based web application using FastAPI. The codebase demonstrates good modern practices with proper dependency management, testing infrastructure, and clear separation of concerns.

## Code Quality: 4/5
The code follows PEP 8 guidelines and uses type hints consistently. Well-structured with clear module separation.

## Security: 3/5
Basic authentication is implemented, but there are some concerns around input validation and session management.

## Architecture: 4/5
Clean layered architecture with separation between API routes, business logic, and data access.

## Operations: 3.5/5
Docker support is present, but monitoring and logging could be improved.

## Documentation: 3/5
README exists but API documentation is minimal. Code comments are sparse.

## Strengths
- Modern FastAPI framework with async support
- Comprehensive test suite with good coverage
- Docker containerization for easy deployment
- Clear project structure and separation of concerns
- Type hints throughout the codebase

## Risks
- Limited input validation on several endpoints
- No rate limiting implemented
- Session management could be more robust
- Missing comprehensive API documentation
- No monitoring or observability tools configured

## Findings

### High Severity
- SQL Injection Risk: User input in search queries not properly parameterized
- Missing Authentication: Several admin endpoints lack authentication middleware
- Secrets in Code: Database credentials hardcoded in configuration file

### Medium Severity
- Missing Rate Limiting: API endpoints vulnerable to abuse without rate limits
- Weak Password Policy: No enforcement of password complexity requirements
- Error Messages Leak Info: Detailed error messages expose internal structure

### Low Severity
- Code Duplication: Several similar validation functions could be consolidated
- Missing Docstrings: Many functions lack documentation
- Outdated Dependencies: Several packages have newer versions available

## Recommendation
This project shows good foundational architecture and development practices. However, the high-severity security findings must be addressed before production deployment. Specifically:

1. Implement parameterized queries to prevent SQL injection
2. Add authentication middleware to all admin endpoints
3. Move secrets to environment variables
4. Add rate limiting to all public endpoints

Once these critical issues are resolved, this would be a YELLOW rating project suitable for production with monitoring.

## Overall Rating: Yellow
"""
