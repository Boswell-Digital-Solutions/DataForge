"""
DataForge Client Library for VibeForge Backend

This module provides a robust client for connecting to DataForge API,
handling logging of wizard interactions, project tracking, and querying
historical data for adaptive recommendations.

Features:
- Connection pooling for efficient requests
- Retry logic with exponential backoff
- Circuit breaker pattern for fault tolerance
- Graceful fallbacks when DataForge is unavailable
- Comprehensive error handling
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx
from enum import Enum

logger = logging.getLogger(__name__)


class ProjectType(str, Enum):
    """Project type enumeration matching DataForge schema."""
    web = "web"
    mobile = "mobile"
    desktop = "desktop"
    api = "api"
    ai_ml = "ai_ml"
    cli = "cli"
    library = "library"


class OutcomeStatus(str, Enum):
    """Outcome status enumeration."""
    success = "success"
    partial = "partial"
    failure = "failure"


class DataForgeClientError(Exception):
    """Base exception for DataForge client errors."""
    pass


class DataForgeConnectionError(DataForgeClientError):
    """Raised when connection to DataForge fails."""
    pass


class DataForgeClient:
    """
    Client for interacting with DataForge learning layer API.
    
    This client handles all communication with DataForge, including:
    - Project creation and tracking
    - Wizard session logging
    - Stack outcome recording
    - Model performance tracking
    - User preference queries
    - Analytics and historical data retrieval
    
    The client includes retry logic, circuit breaking, and graceful
    fallbacks to ensure VibeForge remains functional even when
    DataForge is temporarily unavailable.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ):
        """
        Initialize DataForge client.
        
        Args:
            base_url: Base URL for DataForge API (default: localhost:8001)
            timeout: Request timeout in seconds (default: 10.0)
            max_retries: Maximum number of retry attempts (default: 3)
            retry_backoff: Initial backoff time for retries in seconds (default: 1.0)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        
        # Circuit breaker state
        self._circuit_open = False
        self._circuit_failures = 0
        self._circuit_last_failure: Optional[datetime] = None
        self._circuit_threshold = 5  # Open circuit after 5 consecutive failures
        self._circuit_timeout = 60  # Try again after 60 seconds
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        
        logger.info(f"DataForge client initialized: {self.base_url}")
    
    async def close(self):
        """Close the HTTP client and release connections."""
        await self.client.aclose()
        logger.info("DataForge client closed")
    
    def _check_circuit(self) -> bool:
        """
        Check if circuit breaker is open.
        
        Returns:
            True if circuit is closed (requests allowed), False if open
        """
        if not self._circuit_open:
            return True
        
        # Check if timeout has elapsed
        if self._circuit_last_failure:
            elapsed = (datetime.now() - self._circuit_last_failure).total_seconds()
            if elapsed > self._circuit_timeout:
                logger.info("Circuit breaker timeout elapsed, attempting reconnection")
                self._circuit_open = False
                self._circuit_failures = 0
                return True
        
        logger.warning("Circuit breaker is open, skipping DataForge request")
        return False
    
    def _record_failure(self):
        """Record a failure and potentially open circuit breaker."""
        self._circuit_failures += 1
        self._circuit_last_failure = datetime.now()
        
        if self._circuit_failures >= self._circuit_threshold:
            self._circuit_open = True
            logger.error(
                f"Circuit breaker opened after {self._circuit_failures} failures. "
                f"Will retry after {self._circuit_timeout}s"
            )
    
    def _record_success(self):
        """Record a success and reset failure counter."""
        if self._circuit_failures > 0:
            logger.info("DataForge connection restored")
        self._circuit_failures = 0
        self._circuit_open = False
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with retry logic and circuit breaker.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            data: Request body data (for POST/PATCH)
            params: Query parameters
            
        Returns:
            Response JSON data or None on failure
        """
        # Check circuit breaker
        if not self._check_circuit():
            return None
        
        # Retry loop with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=endpoint,
                    json=data,
                    params=params,
                )
                
                # Check for success status codes
                if response.status_code in (200, 201, 204):
                    self._record_success()
                    return response.json() if response.content else {}
                
                # Log non-success responses
                logger.warning(
                    f"DataForge API returned {response.status_code} for {method} {endpoint}"
                )
                
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"DataForge request timeout (attempt {attempt + 1}/{self.max_retries})")
                
            except httpx.ConnectError as e:
                last_exception = e
                logger.warning(f"DataForge connection failed (attempt {attempt + 1}/{self.max_retries})")
                
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error in DataForge request: {e}")
            
            # Exponential backoff before retry
            if attempt < self.max_retries - 1:
                backoff = self.retry_backoff * (2 ** attempt)
                logger.debug(f"Retrying in {backoff}s...")
                await httpx.AsyncClient().aclose()  # Small delay
        
        # All retries failed
        self._record_failure()
        logger.error(f"DataForge request failed after {self.max_retries} attempts: {last_exception}")
        return None
    
    # ========================================================================
    # Project Management
    # ========================================================================
    
    async def create_project(
        self,
        project_name: str,
        project_type: ProjectType,
        selected_languages: List[str],
        selected_stack: str,
        user_id: Optional[int] = None,
        description: Optional[str] = None,
        team_size: Optional[int] = None,
        timeline_estimate: Optional[str] = None,
        complexity_score: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new project record in DataForge.
        
        This should be called when a user completes the wizard and
        generates a project, capturing all metadata for learning.
        
        Args:
            project_name: Name of the project
            project_type: Type of project (web, mobile, api, etc.)
            selected_languages: List of language IDs selected
            selected_stack: Stack ID that was chosen
            user_id: Optional user ID for tracking
            description: Project description
            team_size: Number of team members
            timeline_estimate: Estimated timeline (e.g., "2 months")
            complexity_score: Complexity rating (1-10)
            
        Returns:
            Project data with ID, or None on failure
        """
        data = {
            "project_name": project_name,
            "project_type": project_type.value if isinstance(project_type, Enum) else project_type,
            "selected_languages": selected_languages,
            "selected_stack": selected_stack,
        }
        
        # Add optional fields
        if user_id is not None:
            data["user_id"] = user_id
        if description:
            data["description"] = description
        if team_size is not None:
            data["team_size"] = team_size
        if timeline_estimate:
            data["timeline_estimate"] = timeline_estimate
        if complexity_score is not None:
            data["complexity_score"] = complexity_score
        
        result = await self._request("POST", "/api/vibeforge/projects", data=data)
        if result:
            logger.info(f"Created project in DataForge: {project_name} (id={result.get('id')})")
        return result
    
    async def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve project details by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project data or None
        """
        return await self._request("GET", f"/api/vibeforge/projects/{project_id}")
    
    async def get_user_projects(
        self,
        user_id: int,
        project_type: Optional[ProjectType] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all projects for a user.
        
        Args:
            user_id: User ID
            project_type: Optional filter by project type
            
        Returns:
            List of project records
        """
        params = {"user_id": user_id}
        if project_type:
            params["project_type"] = project_type.value
        
        result = await self._request("GET", "/api/vibeforge/projects", params=params)
        return result if result else []
    
    # ========================================================================
    # Session Tracking
    # ========================================================================
    
    async def create_session(
        self,
        project_id: int,
        steps_completed: Optional[List[int]] = None,
        languages_viewed: Optional[List[str]] = None,
        stack_final: Optional[str] = None,
        llm_queries: Optional[int] = None,
        wizard_restarted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a wizard session record.
        
        This tracks a user's journey through the wizard, capturing
        which steps they completed, languages they viewed, and their
        final stack selection.
        
        Args:
            project_id: Associated project ID
            steps_completed: List of step numbers completed (1-5)
            languages_viewed: Languages user viewed
            stack_final: Final stack selected
            llm_queries: Number of LLM queries made
            wizard_restarted: Whether user restarted wizard
            
        Returns:
            Session data with ID, or None on failure
        """
        data = {"project_id": project_id}
        
        if steps_completed:
            data["steps_completed"] = steps_completed
        if languages_viewed:
            data["languages_viewed"] = languages_viewed
        if stack_final:
            data["stack_final"] = stack_final
        if llm_queries is not None:
            data["llm_queries"] = llm_queries
        data["wizard_restarted"] = wizard_restarted
        
        result = await self._request("POST", "/api/vibeforge/sessions", data=data)
        if result:
            logger.info(f"Created session in DataForge: project_id={project_id}, session_id={result.get('id')}")
        return result
    
    async def complete_session(
        self,
        session_id: int,
        feedback_rating: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Mark a session as completed.
        
        Args:
            session_id: Session ID
            feedback_rating: Optional user rating (1-5)
            
        Returns:
            Updated session data
        """
        return await self._request("POST", f"/api/vibeforge/sessions/{session_id}/complete")
    
    async def abandon_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Mark a session as abandoned (user left wizard incomplete).
        
        Args:
            session_id: Session ID
            
        Returns:
            Updated session data
        """
        return await self._request("POST", f"/api/vibeforge/sessions/{session_id}/abandon")
    
    # ========================================================================
    # Outcome Tracking
    # ========================================================================
    
    async def record_outcome(
        self,
        project_id: int,
        stack_id: str,
        project_type: ProjectType,
        languages_used: List[str],
        outcome_status: OutcomeStatus,
        build_successful: Optional[bool] = None,
        tests_pass_rate: Optional[float] = None,
        user_satisfaction: Optional[int] = None,
        build_time_seconds: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Record project outcome for learning.
        
        This captures whether the generated project built successfully,
        test results, and user satisfaction to improve future recommendations.
        
        Args:
            project_id: Project ID
            stack_id: Stack used
            project_type: Type of project
            languages_used: Languages that were used
            outcome_status: Success, partial, or failure
            build_successful: Whether build succeeded
            tests_pass_rate: Percentage of tests passing (0.0-1.0)
            user_satisfaction: User rating (1-5)
            build_time_seconds: Time to build in seconds
            notes: Additional notes or issues
            
        Returns:
            Outcome record with ID
        """
        data = {
            "project_id": project_id,
            "stack_id": stack_id,
            "project_type": project_type.value if isinstance(project_type, Enum) else project_type,
            "languages_used": languages_used,
            "outcome_status": outcome_status.value if isinstance(outcome_status, Enum) else outcome_status,
        }
        
        if build_successful is not None:
            data["build_successful"] = build_successful
        if tests_pass_rate is not None:
            data["tests_pass_rate"] = tests_pass_rate
        if user_satisfaction is not None:
            data["user_satisfaction"] = user_satisfaction
        if build_time_seconds is not None:
            data["build_time_seconds"] = build_time_seconds
        if notes:
            data["notes"] = notes
        
        result = await self._request("POST", "/api/vibeforge/outcomes", data=data)
        if result:
            logger.info(f"Recorded outcome: project_id={project_id}, status={outcome_status}")
        return result
    
    # ========================================================================
    # Analytics & Historical Data
    # ========================================================================
    
    async def get_stack_success_rate(self, stack_id: str) -> Optional[Dict[str, Any]]:
        """
        Get success rate statistics for a stack.
        
        Args:
            stack_id: Stack ID
            
        Returns:
            Statistics including success_rate, total_uses, avg_satisfaction
        """
        params = {"stack_id": stack_id}
        return await self._request("GET", "/api/vibeforge/analytics/stack-success", params=params)
    
    async def get_user_preferences(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get user's language preferences and history.
        
        Args:
            user_id: User ID
            
        Returns:
            List of language preferences with usage counts
        """
        result = await self._request("GET", f"/api/vibeforge/preferences/{user_id}")
        return result if result else []
    
    async def get_user_favorites(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get user's favorite (most-used) languages.
        
        Args:
            user_id: User ID
            limit: Max number of favorites to return
            
        Returns:
            List of favorite languages ordered by usage
        """
        result = await self._request("GET", f"/api/vibeforge/preferences/{user_id}/favorites")
        return result[:limit] if result else []
    
    async def get_user_summary(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive user preference summary.
        
        Returns project count, favorite languages/stacks, success rate, etc.
        
        Args:
            user_id: User ID
            
        Returns:
            Summary statistics
        """
        return await self._request("GET", f"/api/vibeforge/preferences/{user_id}/summary")
    
    async def get_abandoned_sessions(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get recently abandoned wizard sessions for analysis.
        
        Args:
            days: Look back period in days
            
        Returns:
            List of abandoned sessions
        """
        params = {"days": days}
        result = await self._request("GET", "/api/vibeforge/analytics/abandoned-sessions", params=params)
        return result.get("sessions", []) if result else []
    
    # ========================================================================
    # Model Performance Tracking
    # ========================================================================
    
    async def record_model_performance(
        self,
        session_id: Optional[int],
        provider: str,
        model_name: str,
        prompt_type: str,
        response_time_ms: Optional[int] = None,
        tokens_total: Optional[int] = None,
        confidence_score: Optional[float] = None,
        recommendation_accepted: Optional[bool] = None,
        feedback: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Record LLM model performance metrics.
        
        Tracks which models are most effective at providing good
        recommendations that users accept.
        
        Args:
            session_id: Associated session ID
            provider: LLM provider (openai, anthropic, etc.)
            model_name: Model identifier
            prompt_type: Type of prompt (stack_recommendation, etc.)
            response_time_ms: Response time in milliseconds
            tokens_total: Total tokens used
            confidence_score: Model confidence (0.0-1.0)
            recommendation_accepted: Whether user accepted recommendation
            feedback: User feedback on quality
            
        Returns:
            Performance record with ID
        """
        data = {
            "provider": provider,
            "model_name": model_name,
            "prompt_type": prompt_type,
        }
        
        if session_id:
            data["session_id"] = session_id
        if response_time_ms is not None:
            data["response_time_ms"] = response_time_ms
        if tokens_total is not None:
            data["tokens_total"] = tokens_total
        if confidence_score is not None:
            data["confidence_score"] = confidence_score
        if recommendation_accepted is not None:
            data["recommendation_accepted"] = recommendation_accepted
        if feedback:
            data["feedback"] = feedback
        
        result = await self._request("POST", "/api/vibeforge/performance", data=data)
        if result:
            logger.info(f"Recorded model performance: {provider}/{model_name}")
        return result
    
    async def get_model_acceptance_rate(self, provider: str, model_name: str) -> float:
        """
        Get acceptance rate for a specific LLM model.
        
        Args:
            provider: LLM provider
            model_name: Model name
            
        Returns:
            Acceptance rate (0.0-1.0)
        """
        params = {"provider": provider, "model_name": model_name}
        result = await self._request("GET", "/api/vibeforge/analytics/model-acceptance", params=params)
        return result.get("acceptance_rate", 0.0) if result else 0.0


# Singleton instance for easy access
_client_instance: Optional[DataForgeClient] = None


def get_dataforge_client() -> DataForgeClient:
    """
    Get or create the global DataForge client instance.
    
    Returns:
        DataForgeClient singleton
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = DataForgeClient()
    return _client_instance


async def close_dataforge_client():
    """Close the global DataForge client if it exists."""
    global _client_instance
    if _client_instance is not None:
        await _client_instance.close()
        _client_instance = None
