"""
End-to-end tests for complete user workflows.
Tests full business processes from start to finish.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app


@pytest.fixture
def e2e_client():
    """Create test client for E2E tests."""
    return TestClient(app)


def create_test_user(client: TestClient, username: str, email: str):
    """Helper to create a test user and return token."""
    user_data = {
        "email": email,
        "username": username,
        "password": "SecureTestPass123!"
    }
    
    # Register
    client.post("/api/auth/register", json=user_data)
    
    # Login
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "SecureTestPass123!"}
    )
    
    return response.json()["access_token"]


@pytest.mark.e2e
class TestUserOnboarding:
    """E2E tests for user onboarding and setup."""
    
    def test_complete_user_registration_flow(self, e2e_client):
        """Test complete user registration, login, and profile setup."""
        # Register
        register_data = {
            "email": "onboarding@test.com",
            "username": "onboard_user",
            "password": "SecurePass123!"
        }
        
        response = e2e_client.post("/api/auth/register", json=register_data)
        assert response.status_code == 200
        
        # Login
        login_response = e2e_client.post(
            "/api/auth/login",
            json={"username": "onboard_user", "password": "SecurePass123!"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Get user profile
        headers = {"Authorization": f"Bearer {token}"}
        profile_response = e2e_client.get("/api/auth/me", headers=headers)
        assert profile_response.status_code == 200
        assert profile_response.json()["username"] == "onboard_user"


@pytest.mark.e2e
class TestProjectWorkflow:
    """E2E tests for complete project workflow."""
    
    def test_project_creation_to_analysis(self, e2e_client):
        """Test creating a project and performing analysis."""
        # Setup user
        token = create_test_user(e2e_client, "analyst", "analyst@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 1: Create project
        project_data = {
            "name": "TechStartup Inc",
            "description": "Early-stage tech startup",
            "industry": "Technology",
            "stage": "Seed",
            "founded_year": 2023,
            "founders": ["Alice", "Bob"]
        }
        
        project_response = e2e_client.post(
            "/api/projects",
            json=project_data,
            headers=headers
        )
        assert project_response.status_code == 200
        project = project_response.json()
        project_id = project["id"]
        
        # Step 2: Verify project created
        get_response = e2e_client.get(
            f"/api/projects/{project_id}",
            headers=headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "TechStartup Inc"
        
        # Step 3: Create due diligence
        diligence_data = {
            "project_id": project_id,
            "review_type": "comprehensive",
            "scope": "Full technical and financial assessment",
            "focus_areas": ["Financial", "Technical", "Team"]
        }
        
        diligence_response = e2e_client.post(
            "/api/diligence",
            json=diligence_data,
            headers=headers
        )
        assert diligence_response.status_code == 200
        diligence = diligence_response.json()
        diligence_id = diligence["id"]
        
        # Step 4: Add findings during review
        findings = [
            {
                "title": "Strong technical team",
                "description": "Team has 10+ years combined experience",
                "severity": "info",
                "category": "Team",
                "status": "open"
            },
            {
                "title": "Early revenue traction",
                "description": "ARR of $50k in first 6 months",
                "severity": "info",
                "category": "Financial",
                "status": "open"
            },
            {
                "title": "Limited market validation",
                "description": "Only 2 enterprise customers",
                "severity": "medium",
                "category": "Market",
                "status": "open"
            }
        ]
        
        finding_ids = []
        for finding in findings:
            response = e2e_client.post(
                f"/api/diligence/{diligence_id}/findings",
                json=finding,
                headers=headers
            )
            assert response.status_code == 200
            finding_ids.append(response.json()["id"])
        
        # Step 5: Get diligence summary
        summary_response = e2e_client.get(
            f"/api/diligence/{diligence_id}",
            headers=headers
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["project_id"] == project_id
        
        # Step 6: Close review
        close_response = e2e_client.post(
            f"/api/diligence/{diligence_id}/close",
            json={"rating": "recommended", "recommendation": "Proceed with investment"},
            headers=headers
        )
        assert close_response.status_code in [200, 201]
        
        # Step 7: Verify closed
        final_response = e2e_client.get(
            f"/api/diligence/{diligence_id}",
            headers=headers
        )
        assert final_response.json()["status"] in ["closed", "completed"]


@pytest.mark.e2e
class TestMultipleReviewers:
    """E2E tests with multiple reviewers."""
    
    def test_collaborative_review(self, e2e_client):
        """Test multiple reviewers working on same project."""
        # Create two users
        reviewer1_token = create_test_user(
            e2e_client, "reviewer1", "reviewer1@test.com"
        )
        reviewer2_token = create_test_user(
            e2e_client, "reviewer2", "reviewer2@test.com"
        )
        
        headers1 = {"Authorization": f"Bearer {reviewer1_token}"}
        headers2 = {"Authorization": f"Bearer {reviewer2_token}"}
        
        # Reviewer 1: Create project
        project_response = e2e_client.post(
            "/api/projects",
            json={"name": "Shared Project", "industry": "Tech"},
            headers=headers1
        )
        project_id = project_response.json()["id"]
        
        # Reviewer 1: Create diligence
        diligence_response = e2e_client.post(
            "/api/diligence",
            json={"project_id": project_id, "review_type": "technical"},
            headers=headers1
        )
        diligence_id = diligence_response.json()["id"]
        
        # Reviewer 1: Add findings
        response1 = e2e_client.post(
            f"/api/diligence/{diligence_id}/findings",
            json={
                "title": "Code quality excellent",
                "category": "Technical",
                "severity": "info",
                "status": "open"
            },
            headers=headers1
        )
        assert response1.status_code == 200
        
        # Reviewer 2: Add findings to same review
        response2 = e2e_client.post(
            f"/api/diligence/{diligence_id}/findings",
            json={
                "title": "Architecture well documented",
                "category": "Technical",
                "severity": "info",
                "status": "open"
            },
            headers=headers2
        )
        assert response2.status_code == 200
        
        # Both can view the findings
        diligence_get = e2e_client.get(
            f"/api/diligence/{diligence_id}",
            headers=headers1
        )
        assert diligence_get.status_code == 200


@pytest.mark.e2e
class TestReportGeneration:
    """E2E tests for report generation."""
    
    def test_generate_diligence_report(self, e2e_client):
        """Test complete report generation workflow."""
        # Setup
        token = create_test_user(e2e_client, "reporter", "reporter@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create complete diligence
        project_response = e2e_client.post(
            "/api/projects",
            json={"name": "Report Test Co", "industry": "Tech"},
            headers=headers
        )
        project_id = project_response.json()["id"]
        
        diligence_response = e2e_client.post(
            "/api/diligence",
            json={"project_id": project_id, "review_type": "comprehensive"},
            headers=headers
        )
        diligence_id = diligence_response.json()["id"]
        
        # Add findings
        for i in range(3):
            e2e_client.post(
                f"/api/diligence/{diligence_id}/findings",
                json={
                    "title": f"Finding {i}",
                    "category": "General",
                    "severity": "info",
                    "status": "open"
                },
                headers=headers
            )
        
        # Close review
        e2e_client.post(
            f"/api/diligence/{diligence_id}/close",
            json={"rating": "recommended"},
            headers=headers
        )
        
        # Generate report
        report_response = e2e_client.get(
            f"/api/diligence/{diligence_id}/report",
            headers=headers
        )
        assert report_response.status_code == 200
        
        # Verify report format
        report = report_response.json()
        assert "project_id" in report
        assert "findings_summary" in report or "findings" in report


@pytest.mark.e2e
class TestSearchWorkflow:
    """E2E tests for search and discovery."""
    
    def test_search_and_filter_projects(self, e2e_client):
        """Test searching and filtering across projects."""
        # Setup
        token = create_test_user(e2e_client, "searcher", "searcher@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create diverse projects
        projects = [
            {"name": "TechAI Corp", "industry": "Technology", "stage": "Series A"},
            {"name": "BioMed Labs", "industry": "Healthcare", "stage": "Seed"},
            {"name": "GreenEnergy Inc", "industry": "Energy", "stage": "Series B"},
            {"name": "FinTech Solutions", "industry": "Finance", "stage": "Series A"},
        ]
        
        for proj in projects:
            e2e_client.post("/api/projects", json=proj, headers=headers)
        
        # Search for "Tech"
        search_response = e2e_client.get(
            "/api/search?q=Tech",
            headers=headers
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) >= 2  # TechAI and FinTech
        
        # Filter by industry
        filter_response = e2e_client.get(
            "/api/search?industry=Technology",
            headers=headers
        )
        assert filter_response.status_code == 200
        filtered = filter_response.json()
        assert all(p.get("industry") == "Technology" for p in filtered)
        
        # Combined search and filter
        combined_response = e2e_client.get(
            "/api/search?q=Series&stage=Series%20A",
            headers=headers
        )
        assert combined_response.status_code == 200


@pytest.mark.e2e
class TestErrorRecovery:
    """E2E tests for error handling and recovery."""
    
    def test_handle_network_error_recovery(self, e2e_client):
        """Test recovery from transient errors."""
        token = create_test_user(e2e_client, "resilient", "resilient@test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create project (may succeed or fail initially)
        for attempt in range(3):
            response = e2e_client.post(
                "/api/projects",
                json={"name": f"Resilience Test {attempt}", "industry": "Tech"},
                headers=headers
            )
            if response.status_code == 200:
                break
        
        assert response.status_code == 200
        project_id = response.json()["id"]
        
        # Verify project was created
        verify_response = e2e_client.get(
            f"/api/projects/{project_id}",
            headers=headers
        )
        assert verify_response.status_code == 200


@pytest.mark.e2e
class TestComplexWorkflows:
    """E2E tests for complex multi-step workflows."""
    
    def test_end_to_end_investment_evaluation(self, e2e_client):
        """Test complete investment evaluation workflow."""
        # Setup team
        due_diligence_lead = create_test_user(
            e2e_client, "dd_lead", "dd_lead@test.com"
        )
        tech_reviewer = create_test_user(
            e2e_client, "tech_lead", "tech_lead@test.com"
        )
        
        headers_dd = {"Authorization": f"Bearer {due_diligence_lead}"}
        headers_tech = {"Authorization": f"Bearer {tech_reviewer}"}
        
        # DD Lead: Create company profile
        company_response = e2e_client.post(
            "/api/projects",
            json={
                "name": "InnovateTech",
                "industry": "AI/ML",
                "stage": "Series B",
                "description": "AI-powered analytics platform"
            },
            headers=headers_dd
        )
        company_id = company_response.json()["id"]
        
        # DD Lead: Initiate comprehensive review
        review_response = e2e_client.post(
            "/api/diligence",
            json={
                "project_id": company_id,
                "review_type": "comprehensive",
                "scope": "Full investment evaluation"
            },
            headers=headers_dd
        )
        review_id = review_response.json()["id"]
        
        # DD Lead: Add financial findings
        financial_findings = [
            {"title": "Strong revenue growth", "category": "Financial", "severity": "info"},
            {"title": "Healthy unit economics", "category": "Financial", "severity": "info"},
        ]
        for finding in financial_findings:
            e2e_client.post(
                f"/api/diligence/{review_id}/findings",
                json=finding,
                headers=headers_dd
            )
        
        # Tech Lead: Add technical findings
        tech_findings = [
            {"title": "Scalable infrastructure", "category": "Technical", "severity": "info"},
            {"title": "Good engineering practices", "category": "Technical", "severity": "info"},
        ]
        for finding in tech_findings:
            e2e_client.post(
                f"/api/diligence/{review_id}/findings",
                json=finding,
                headers=headers_tech
            )
        
        # DD Lead: Complete review with recommendation
        close_response = e2e_client.post(
            f"/api/diligence/{review_id}/close",
            json={
                "rating": "recommended",
                "recommendation": "Proceed with Series B investment",
                "investment_amount": 5000000
            },
            headers=headers_dd
        )
        assert close_response.status_code in [200, 201]
        
        # Get final report
        report_response = e2e_client.get(
            f"/api/diligence/{review_id}/report",
            headers=headers_dd
        )
        assert report_response.status_code == 200
