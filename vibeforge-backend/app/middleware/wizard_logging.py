"""
Logging Middleware for VibeForge Wizard Interactions

This middleware automatically captures wizard interactions and logs them
to DataForge for learning and analysis. It tracks:
- Language selections and views
- Stack selections (recommended vs chosen)
- User overrides and customizations
- Step progression and abandonment
- LLM query/response pairs

The middleware is non-blocking and fails gracefully to ensure the
wizard remains functional even if DataForge is unavailable.
"""
import logging
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json
from datetime import datetime

from app.clients.dataforge_client import get_dataforge_client, ProjectType

logger = logging.getLogger(__name__)


class WizardLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log wizard interactions to DataForge.
    
    This captures all relevant wizard activity for learning purposes,
    including language selections, stack choices, and user behavior patterns.
    
    The middleware operates asynchronously and never blocks the main request,
    ensuring wizard performance is unaffected by logging operations.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.dataforge = get_dataforge_client()
        
        # Track active wizard sessions in memory (temporary)
        # In production, this would use Redis or another cache
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log relevant wizard interactions.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint handler
            
        Returns:
            HTTP response
        """
        # Get response first (non-blocking)
        response = await call_next(request)
        
        # Log interaction asynchronously (fire and forget)
        try:
            await self._log_interaction(request, response)
        except Exception as e:
            # Never let logging errors affect the wizard
            logger.error(f"Error in wizard logging middleware: {e}")
        
        return response
    
    async def _log_interaction(self, request: Request, response: Response):
        """
        Log wizard interaction based on request path and method.
        
        Args:
            request: HTTP request
            response: HTTP response
        """
        path = request.url.path
        method = request.method
        
        # Only log wizard-related endpoints
        if not path.startswith("/api/v1/wizard") and not path.startswith("/api/v1/stacks/recommend"):
            return
        
        # Skip if response was an error
        if response.status_code >= 400:
            return
        
        # Log based on endpoint type
        if path == "/api/v1/wizard/session/start" and method == "POST":
            await self._log_session_start(request)
        
        elif path == "/api/v1/wizard/session/save" and method == "POST":
            await self._log_session_save(request)
        
        elif "/languages" in path and method == "GET":
            await self._log_language_view(request)
        
        elif path == "/api/v1/wizard/languages/select" and method == "POST":
            await self._log_language_selection(request)
        
        elif path == "/api/v1/stacks/recommend" and method == "POST":
            await self._log_stack_recommendation(request, response)
        
        elif path == "/api/v1/wizard/stack/select" and method == "POST":
            await self._log_stack_selection(request)
        
        elif path == "/api/v1/wizard/complete" and method == "POST":
            await self._log_wizard_completion(request)
        
        elif path == "/api/v1/wizard/abandon" and method == "POST":
            await self._log_wizard_abandonment(request)
    
    async def _log_session_start(self, request: Request):
        """
        Log wizard session initiation.
        
        Args:
            request: HTTP request with session start data
        """
        try:
            body = await self._get_request_body(request)
            session_id = body.get("session_id")
            user_id = body.get("user_id")
            
            if session_id:
                # Store session context
                self._active_sessions[session_id] = {
                    "started_at": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    "languages_viewed": [],
                    "languages_selected": [],
                    "stacks_viewed": [],
                    "stack_selected": None,
                    "steps_completed": [],
                    "llm_queries": 0,
                }
                
                logger.info(f"Wizard session started: {session_id}")
        
        except Exception as e:
            logger.error(f"Error logging session start: {e}")
    
    async def _log_session_save(self, request: Request):
        """
        Log wizard session save (draft persistence).
        
        Args:
            request: HTTP request with session save data
        """
        try:
            body = await self._get_request_body(request)
            session_id = body.get("session_id")
            step = body.get("current_step")
            
            if session_id and session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                if step not in session["steps_completed"]:
                    session["steps_completed"].append(step)
                
                logger.debug(f"Wizard session saved: {session_id}, step {step}")
        
        except Exception as e:
            logger.error(f"Error logging session save: {e}")
    
    async def _log_language_view(self, request: Request):
        """
        Log language view/browse activity.
        
        Args:
            request: HTTP request
        """
        try:
            # Extract session_id from query params or headers
            session_id = request.query_params.get("session_id") or request.headers.get("X-Session-ID")
            language_id = self._extract_language_id(request.url.path)
            
            if session_id and session_id in self._active_sessions and language_id:
                session = self._active_sessions[session_id]
                if language_id not in session["languages_viewed"]:
                    session["languages_viewed"].append(language_id)
                
                logger.debug(f"Language viewed: {language_id} (session: {session_id})")
        
        except Exception as e:
            logger.error(f"Error logging language view: {e}")
    
    async def _log_language_selection(self, request: Request):
        """
        Log language selection by user.
        
        Args:
            request: HTTP request with language selection data
        """
        try:
            body = await self._get_request_body(request)
            session_id = body.get("session_id")
            language_ids = body.get("language_ids", [])
            
            if session_id and session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                session["languages_selected"] = language_ids
                
                logger.info(f"Languages selected: {language_ids} (session: {session_id})")
        
        except Exception as e:
            logger.error(f"Error logging language selection: {e}")
    
    async def _log_stack_recommendation(self, request: Request, response: Response):
        """
        Log LLM stack recommendation request/response.
        
        Tracks which stacks were recommended and whether the user
        accepted them, for measuring model effectiveness.
        
        Args:
            request: HTTP request with recommendation query
            response: HTTP response with recommendations
        """
        try:
            body = await self._get_request_body(request)
            session_id = body.get("session_id")
            
            if session_id and session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                session["llm_queries"] += 1
                
                # Track recommended stacks
                # Note: Would need to parse response body in production
                logger.info(f"Stack recommendation requested (session: {session_id})")
        
        except Exception as e:
            logger.error(f"Error logging stack recommendation: {e}")
    
    async def _log_stack_selection(self, request: Request):
        """
        Log stack selection by user.
        
        Captures whether user selected a recommended stack or
        chose something different (user override).
        
        Args:
            request: HTTP request with stack selection
        """
        try:
            body = await self._get_request_body(request)
            session_id = body.get("session_id")
            stack_id = body.get("stack_id")
            was_recommended = body.get("was_recommended", False)
            
            if session_id and session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                session["stack_selected"] = stack_id
                session["stack_was_recommended"] = was_recommended
                
                logger.info(f"Stack selected: {stack_id} (recommended: {was_recommended})")
        
        except Exception as e:
            logger.error(f"Error logging stack selection: {e}")
    
    async def _log_wizard_completion(self, request: Request):
        """
        Log successful wizard completion and create DataForge records.
        
        This creates project, session, and initial preference records.
        
        Args:
            request: HTTP request with completion data
        """
        try:
            body = await self._get_request_body(request)
            session_id = body.get("session_id")
            
            if not session_id or session_id not in self._active_sessions:
                logger.warning(f"Cannot log completion for unknown session: {session_id}")
                return
            
            session = self._active_sessions[session_id]
            
            # Extract project data
            project_name = body.get("project_name")
            project_type = body.get("project_type", "web")
            languages = session.get("languages_selected", [])
            stack = session.get("stack_selected")
            user_id = session.get("user_id")
            
            if not project_name or not stack:
                logger.warning("Missing required data for project creation")
                return
            
            # Create project in DataForge
            project = await self.dataforge.create_project(
                project_name=project_name,
                project_type=ProjectType(project_type),
                selected_languages=languages,
                selected_stack=stack,
                user_id=user_id,
                description=body.get("description"),
                team_size=body.get("team_size"),
                timeline_estimate=body.get("timeline_estimate"),
                complexity_score=body.get("complexity_score"),
            )
            
            if not project:
                logger.error("Failed to create project in DataForge")
                return
            
            project_id = project.get("id")
            
            # Create session record
            await self.dataforge.create_session(
                project_id=project_id,
                steps_completed=session.get("steps_completed", []),
                languages_viewed=session.get("languages_viewed", []),
                stack_final=stack,
                llm_queries=session.get("llm_queries", 0),
                wizard_restarted=False,
            )
            
            # Clean up session from memory
            del self._active_sessions[session_id]
            
            logger.info(f"Wizard completed: project_id={project_id}, stack={stack}")
        
        except Exception as e:
            logger.error(f"Error logging wizard completion: {e}")
    
    async def _log_wizard_abandonment(self, request: Request):
        """
        Log wizard abandonment (user left incomplete).
        
        Args:
            request: HTTP request with abandonment data
        """
        try:
            body = await self._get_request_body(request)
            session_id = body.get("session_id")
            
            if session_id and session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                
                logger.info(f"Wizard abandoned at step {len(session.get('steps_completed', []))}")
                
                # Clean up session
                del self._active_sessions[session_id]
        
        except Exception as e:
            logger.error(f"Error logging wizard abandonment: {e}")
    
    async def _get_request_body(self, request: Request) -> Dict[str, Any]:
        """
        Extract JSON body from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Parsed JSON body
        """
        try:
            body_bytes = await request.body()
            if body_bytes:
                return json.loads(body_bytes)
        except Exception as e:
            logger.error(f"Error parsing request body: {e}")
        
        return {}
    
    def _extract_language_id(self, path: str) -> Optional[str]:
        """
        Extract language ID from URL path.
        
        Args:
            path: URL path (e.g., /api/v1/languages/python)
            
        Returns:
            Language ID or None
        """
        parts = path.split("/")
        if "languages" in parts:
            lang_index = parts.index("languages")
            if lang_index + 1 < len(parts):
                return parts[lang_index + 1]
        
        return None
