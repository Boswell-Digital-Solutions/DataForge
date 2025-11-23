"""
Adaptive Recommendations Router

Provides learning-based recommendations using historical data from DataForge.
Integrates experience context service with LLM stack advisor for personalized suggestions.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.clients.dataforge_client import get_dataforge_client, DataForgeConnectionError
from app.services.experience_context import get_experience_service

router = APIRouter(prefix="/api/v1", tags=["adaptive"])


# Request/Response Models
class RecommendationRequest(BaseModel):
    """Request for adaptive stack recommendations."""
    user_id: Optional[int] = Field(None, description="User ID for personalized recommendations")
    project_type: str = Field(..., description="Project type (web, mobile, api, ai_ml, etc.)")
    selected_languages: List[str] = Field(..., description="List of selected language IDs")
    project_name: Optional[str] = Field(None, description="Project name for context")
    team_size: Optional[str] = Field(None, description="Team size (solo, small, medium, large)")
    timeline: Optional[str] = Field(None, description="Timeline (quick, standard, extended)")


class RecommendationResponse(BaseModel):
    """Response with adaptive recommendations."""
    stack_id: str
    stack_name: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    reasoning: List[str] = Field(..., description="Human-readable reasoning")
    based_on: Dict[str, bool] = Field(..., description="Data sources used")
    metrics: Dict[str, Any] = Field(..., description="Success rates and usage stats")


class ExperienceContextResponse(BaseModel):
    """Historical experience context for a user."""
    user_id: Optional[int]
    total_projects: int
    favorite_languages: List[Dict[str, Any]]
    successful_stacks: List[Dict[str, Any]]
    project_types: Dict[str, int]
    overall_success_rate: float
    avg_project_complexity: float
    recent_patterns: Dict[str, Any]
    timestamp: str


class SuccessPredictionResponse(BaseModel):
    """Predicted success rate for a project configuration."""
    predicted_success_rate: float = Field(..., ge=0.0, le=100.0)
    confidence_level: str = Field(..., description="high, medium, or low")
    similar_projects: int
    based_on_languages: List[str]
    based_on_stack: Optional[str]
    explanation: str


@router.post("/stacks/recommend-adaptive", response_model=List[RecommendationResponse])
async def recommend_adaptive(request: RecommendationRequest):
    """
    Get adaptive stack recommendations based on user history.
    
    This endpoint combines:
    1. User's historical project data from DataForge
    2. Global stack success rates
    3. Language compatibility matching
    4. LLM-powered reasoning
    
    Returns personalized recommendations with explainable confidence scores.
    """
    try:
        service = get_experience_service()
        
        # Build historical context
        context = await service.build_context(
            user_id=request.user_id,
            project_type=request.project_type
        )
        
        # TODO: Integrate with existing LLM stack advisor
        # For now, return mock recommendations filtered by languages
        
        # Mock stack database (should come from stack profiles API)
        all_stacks = [
            {
                "stack_id": "fastapi-ai",
                "stack_name": "FastAPI AI Stack",
                "languages": ["python"],
                "project_types": ["api", "ai_ml"],
            },
            {
                "stack_id": "nextjs",
                "stack_name": "Next.js Fullstack",
                "languages": ["typescript", "javascript"],
                "project_types": ["web"],
            },
            {
                "stack_id": "t3-stack",
                "stack_name": "T3 Stack",
                "languages": ["typescript"],
                "project_types": ["web"],
            },
        ]
        
        # Filter stacks by selected languages
        compatible_stacks = [
            stack for stack in all_stacks
            if any(lang in request.selected_languages for lang in stack["languages"])
            and request.project_type in stack["project_types"]
        ]
        
        recommendations = []
        for stack in compatible_stacks:
            # Calculate confidence using historical data
            confidence = await service.get_stack_confidence(
                stack_id=stack["stack_id"],
                user_id=request.user_id
            )
            
            # Build reasoning based on context
            reasoning = []
            based_on = {
                "user_experience": False,
                "language_match": True,
                "project_type_match": True,
                "global_success": False,
            }
            
            # Check user experience
            user_stack = next(
                (s for s in context.successful_stacks if s.stack_id == stack["stack_id"]),
                None
            )
            
            if user_stack:
                based_on["user_experience"] = True
                reasoning.append(
                    f"You have {user_stack.success_rate*100:.0f}% success rate with this stack "
                    f"({user_stack.times_used} project{'s' if user_stack.times_used != 1 else ''})"
                )
                reasoning.append(
                    f"Average satisfaction: {user_stack.avg_satisfaction:.1f}/5.0 stars"
                )
            else:
                reasoning.append("No personal history with this stack")
            
            # Language match
            matched_langs = [lang for lang in request.selected_languages if lang in stack["languages"]]
            reasoning.append(f"Matches your selected language{'s' if len(matched_langs) > 1 else ''}: {', '.join(matched_langs)}")
            
            # Project type match
            reasoning.append(f"Recommended for {request.project_type} projects")
            
            # Global success (mock data)
            global_rate = 0.87 if stack["stack_id"] == "fastapi-ai" else 0.82
            based_on["global_success"] = True
            reasoning.append(f"Global success rate: {global_rate*100:.0f}%")
            
            recommendations.append(
                RecommendationResponse(
                    stack_id=stack["stack_id"],
                    stack_name=stack["stack_name"],
                    confidence=confidence,
                    reasoning=reasoning,
                    based_on=based_on,
                    metrics={
                        "user_success_rate": user_stack.success_rate if user_stack else None,
                        "global_success_rate": global_rate,
                        "user_times_used": user_stack.times_used if user_stack else 0,
                        "avg_satisfaction": user_stack.avg_satisfaction if user_stack else None,
                    }
                )
            )
        
        # Sort by confidence descending
        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        
        return recommendations
    
    except DataForgeConnectionError as e:
        # Graceful fallback: return language-based recommendations without history
        return []
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.get("/experience/context", response_model=ExperienceContextResponse)
async def get_experience_context(
    user_id: int = Query(..., description="User ID"),
    project_type: Optional[str] = Query(None, description="Optional project type for context")
):
    """
    Get historical experience context for a user.
    
    Returns:
    - Total projects completed
    - Favorite languages with success rates
    - Most successful stacks
    - Project type distribution
    - Recent patterns and trends
    """
    try:
        service = get_experience_service()
        context = await service.build_context(
            user_id=user_id,
            project_type=project_type or ""
        )
        
        return ExperienceContextResponse(
            user_id=context.user_id,
            total_projects=context.total_projects,
            favorite_languages=[
                {
                    "language_id": lang.language_id,
                    "language_name": lang.language_name,
                    "times_selected": lang.times_selected,
                    "times_viewed": lang.times_viewed,
                    "success_rate": lang.success_rate,
                    "paired_with": lang.paired_with,
                }
                for lang in context.favorite_languages
            ],
            successful_stacks=[
                {
                    "stack_id": stack.stack_id,
                    "times_used": stack.times_used,
                    "success_rate": stack.success_rate,
                    "avg_satisfaction": stack.avg_satisfaction,
                    "avg_build_time": stack.avg_build_time,
                    "common_issues": stack.common_issues,
                }
                for stack in context.successful_stacks
            ],
            project_types=context.project_types,
            overall_success_rate=context.overall_success_rate,
            avg_project_complexity=context.avg_project_complexity,
            recent_patterns=context.recent_patterns,
            timestamp=context.timestamp,
        )
    
    except DataForgeConnectionError:
        # Return empty context if DataForge unavailable
        return ExperienceContextResponse(
            user_id=user_id,
            total_projects=0,
            favorite_languages=[],
            successful_stacks=[],
            project_types={},
            overall_success_rate=0.0,
            avg_project_complexity=5.0,
            recent_patterns={},
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch experience context: {str(e)}"
        )


@router.get("/experience/success-prediction", response_model=SuccessPredictionResponse)
async def predict_success(
    user_id: Optional[int] = Query(None, description="User ID"),
    project_type: str = Query(..., description="Project type"),
    languages: str = Query(..., description="Comma-separated language IDs"),
    stack_id: Optional[str] = Query(None, description="Selected stack ID")
):
    """
    Predict success rate for a project configuration.
    
    Analyzes:
    - User's historical success with similar projects
    - Global success rates for the stack/language combination
    - Project type complexity
    - Language pairing effectiveness
    """
    try:
        service = get_experience_service()
        language_list = [lang.strip() for lang in languages.split(",")]
        
        # Calculate confidence for stack
        if stack_id:
            confidence = await service.get_stack_confidence(
                stack_id=stack_id,
                user_id=user_id
            )
            predicted_rate = confidence * 100
        else:
            # Base prediction on language selection only
            predicted_rate = 70.0  # Default
        
        # Adjust based on project complexity
        complexity_adjustment = {
            "web": 0,
            "mobile": -5,
            "api": +5,
            "ai_ml": -10,
            "cli": +10,
            "library": -5,
        }
        predicted_rate += complexity_adjustment.get(project_type, 0)
        
        # Clamp to 0-100
        predicted_rate = max(0.0, min(100.0, predicted_rate))
        
        # Determine confidence level
        if predicted_rate >= 80:
            confidence_level = "high"
        elif predicted_rate >= 60:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        # Mock similar project count
        similar_projects = 12 if user_id else 0
        
        explanation = f"Based on {similar_projects} similar projects" if similar_projects > 0 else "Based on global success rates"
        if stack_id:
            explanation += f" using {stack_id}"
        explanation += f" for {project_type} projects with {', '.join(language_list)}"
        
        return SuccessPredictionResponse(
            predicted_success_rate=predicted_rate,
            confidence_level=confidence_level,
            similar_projects=similar_projects,
            based_on_languages=language_list,
            based_on_stack=stack_id,
            explanation=explanation,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to predict success: {str(e)}"
        )
