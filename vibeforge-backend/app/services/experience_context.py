"""
Experience Context Service for VibeForge

This service queries DataForge to build historical context about user
preferences, project patterns, and stack success rates. This context
is used to enhance LLM prompts for more personalized recommendations.

Features:
- Query user's historical projects
- Retrieve language preferences and favorites
- Calculate stack success rates
- Build context objects for LLM prompts
- Generate explainable recommendations
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from app.clients.dataforge_client import get_dataforge_client, ProjectType

logger = logging.getLogger(__name__)


@dataclass
class LanguagePreference:
    """User's preference data for a language."""
    language_id: str
    language_name: str
    times_selected: int
    times_viewed: int
    success_rate: float
    paired_with: List[str]  # Other languages frequently used with this one


@dataclass
class StackExperience:
    """Historical experience with a stack."""
    stack_id: str
    times_used: int
    success_rate: float
    avg_satisfaction: float
    avg_build_time: int
    common_issues: List[str]


@dataclass
class ExperienceContext:
    """
    Complete historical context for making adaptive recommendations.
    
    This context object is passed to LLM prompts to enable
    personalized, history-aware recommendations.
    """
    user_id: Optional[int]
    total_projects: int
    favorite_languages: List[LanguagePreference]
    successful_stacks: List[StackExperience]
    project_types: Dict[str, int]  # Frequency by type
    overall_success_rate: float
    avg_project_complexity: float
    recent_patterns: Dict[str, Any]
    timestamp: str


class ExperienceContextService:
    """
    Service for querying and aggregating historical context from DataForge.
    
    This service builds rich context objects that capture user behavior
    patterns, preferences, and outcomes to enable adaptive recommendations.
    """
    
    def __init__(self):
        """Initialize the service with DataForge client."""
        self.dataforge = get_dataforge_client()
    
    async def build_context(
        self,
        user_id: Optional[int] = None,
        project_type: Optional[ProjectType] = None,
        include_anonymous: bool = True,
    ) -> ExperienceContext:
        """
        Build complete experience context for a user.
        
        This queries DataForge for all relevant historical data and
        aggregates it into a context object suitable for LLM prompts.
        
        Args:
            user_id: User ID to build context for (None for anonymous)
            project_type: Optional filter for specific project type
            include_anonymous: Include anonymous usage data for context
            
        Returns:
            ExperienceContext with all historical data
        """
        logger.info(f"Building experience context for user_id={user_id}")
        
        # If no user_id, return empty context
        if not user_id:
            return self._empty_context()
        
        try:
            # Query user summary from DataForge
            summary = await self.dataforge.get_user_summary(user_id)
            
            if not summary:
                logger.warning(f"No summary data found for user_id={user_id}")
                return self._empty_context()
            
            # Build favorite languages with preference data
            favorites = await self._build_language_preferences(user_id, summary)
            
            # Build successful stack experiences
            successful_stacks = await self._build_stack_experiences(user_id, summary)
            
            # Extract project type distribution
            project_types = summary.get("preferred_project_types", {})
            
            # Calculate overall metrics
            total_projects = summary.get("total_projects", 0)
            success_rate = summary.get("success_rate", 0.0)
            avg_complexity = summary.get("avg_complexity", 5.0)
            
            # Get recent patterns
            recent_patterns = await self._analyze_recent_patterns(user_id)
            
            context = ExperienceContext(
                user_id=user_id,
                total_projects=total_projects,
                favorite_languages=favorites,
                successful_stacks=successful_stacks,
                project_types=project_types,
                overall_success_rate=success_rate,
                avg_project_complexity=avg_complexity,
                recent_patterns=recent_patterns,
                timestamp=datetime.utcnow().isoformat(),
            )
            
            logger.info(
                f"Built context: {total_projects} projects, "
                f"{len(favorites)} favorite languages, "
                f"{success_rate:.1%} success rate"
            )
            
            return context
        
        except Exception as e:
            logger.error(f"Error building experience context: {e}")
            return self._empty_context()
    
    async def _build_language_preferences(
        self,
        user_id: int,
        summary: Dict[str, Any],
    ) -> List[LanguagePreference]:
        """
        Build language preference objects from user data.
        
        Args:
            user_id: User ID
            summary: User summary from DataForge
            
        Returns:
            List of LanguagePreference objects
        """
        try:
            # Get detailed preferences from DataForge
            prefs = await self.dataforge.get_user_preferences(user_id)
            
            language_prefs = []
            for pref in prefs:
                # Calculate success rate for this language
                # (Would need outcome data by language in production)
                success_rate = 0.75  # Placeholder
                
                language_prefs.append(LanguagePreference(
                    language_id=pref.get("language_id"),
                    language_name=pref.get("language_name"),
                    times_selected=pref.get("times_selected", 0),
                    times_viewed=pref.get("times_viewed", 0),
                    success_rate=success_rate,
                    paired_with=list(pref.get("paired_with_languages", {}).keys()),
                ))
            
            # Sort by usage frequency
            language_prefs.sort(key=lambda x: x.times_selected, reverse=True)
            
            return language_prefs[:10]  # Top 10
        
        except Exception as e:
            logger.error(f"Error building language preferences: {e}")
            return []
    
    async def _build_stack_experiences(
        self,
        user_id: int,
        summary: Dict[str, Any],
    ) -> List[StackExperience]:
        """
        Build stack experience objects from user's project history.
        
        Args:
            user_id: User ID
            summary: User summary from DataForge
            
        Returns:
            List of StackExperience objects
        """
        try:
            # Get user's projects
            projects = await self.dataforge.get_user_projects(user_id)
            
            # Aggregate by stack
            stack_data: Dict[str, Dict[str, Any]] = {}
            
            for project in projects:
                stack_id = project.get("selected_stack")
                if not stack_id:
                    continue
                
                if stack_id not in stack_data:
                    stack_data[stack_id] = {
                        "times_used": 0,
                        "successes": 0,
                        "total_satisfaction": 0,
                        "satisfaction_count": 0,
                        "total_build_time": 0,
                        "build_time_count": 0,
                    }
                
                stack_data[stack_id]["times_used"] += 1
                
                # Query outcomes for this stack (would be more efficient with a dedicated endpoint)
                # For now, use stack success rate endpoint
                stats = await self.dataforge.get_stack_success_rate(stack_id)
                if stats:
                    stack_data[stack_id]["success_rate"] = stats.get("success_rate", 0.0)
                    stack_data[stack_id]["avg_satisfaction"] = stats.get("avg_satisfaction", 3.0)
                    stack_data[stack_id]["avg_build_time"] = stats.get("avg_build_time_seconds", 60)
            
            # Build StackExperience objects
            experiences = []
            for stack_id, data in stack_data.items():
                experiences.append(StackExperience(
                    stack_id=stack_id,
                    times_used=data["times_used"],
                    success_rate=data.get("success_rate", 0.5),
                    avg_satisfaction=data.get("avg_satisfaction", 3.0),
                    avg_build_time=data.get("avg_build_time", 60),
                    common_issues=[],  # Would need issue tracking
                ))
            
            # Sort by success rate and usage
            experiences.sort(key=lambda x: (x.success_rate, x.times_used), reverse=True)
            
            return experiences[:10]  # Top 10
        
        except Exception as e:
            logger.error(f"Error building stack experiences: {e}")
            return []
    
    async def _analyze_recent_patterns(self, user_id: int) -> Dict[str, Any]:
        """
        Analyze recent project patterns for trend detection.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with recent patterns and trends
        """
        try:
            # Get recent projects (last 30 days)
            # Note: Would need a "recent projects" endpoint or time filtering
            projects = await self.dataforge.get_user_projects(user_id)
            
            patterns = {
                "trending_up": [],  # Languages/stacks increasing in usage
                "trending_down": [],  # Languages/stacks decreasing
                "new_explorations": [],  # Recently tried for first time
                "abandoned_projects": 0,  # Recent abandonment count
            }
            
            # Analyze patterns (simplified version)
            # In production, this would do time-series analysis
            
            return patterns
        
        except Exception as e:
            logger.error(f"Error analyzing recent patterns: {e}")
            return {}
    
    def _empty_context(self) -> ExperienceContext:
        """
        Create empty context for new users or failures.
        
        Returns:
            Empty ExperienceContext
        """
        return ExperienceContext(
            user_id=None,
            total_projects=0,
            favorite_languages=[],
            successful_stacks=[],
            project_types={},
            overall_success_rate=0.0,
            avg_project_complexity=5.0,
            recent_patterns={},
            timestamp=datetime.utcnow().isoformat(),
        )
    
    def format_for_llm(self, context: ExperienceContext) -> str:
        """
        Format experience context as text for LLM prompts.
        
        This creates a natural language summary of the user's
        historical context that can be included in prompts.
        
        Args:
            context: ExperienceContext to format
            
        Returns:
            Formatted text for LLM prompt
        """
        if context.total_projects == 0:
            return "This is a new user with no project history."
        
        lines = [
            f"User Experience Context:",
            f"- Total projects: {context.total_projects}",
            f"- Overall success rate: {context.overall_success_rate:.1%}",
            f"- Average complexity: {context.avg_project_complexity:.1f}/10",
            "",
        ]
        
        # Favorite languages
        if context.favorite_languages:
            lines.append("Favorite languages:")
            for lang in context.favorite_languages[:5]:
                lines.append(f"  • {lang.language_name} ({lang.times_selected} projects, {lang.success_rate:.1%} success)")
            lines.append("")
        
        # Successful stacks
        if context.successful_stacks:
            lines.append("Most successful stacks:")
            for stack in context.successful_stacks[:3]:
                lines.append(
                    f"  • {stack.stack_id}: {stack.times_used} uses, "
                    f"{stack.success_rate:.1%} success, "
                    f"{stack.avg_satisfaction:.1f}/5 satisfaction"
                )
            lines.append("")
        
        # Project types
        if context.project_types:
            lines.append("Project type distribution:")
            for ptype, count in sorted(context.project_types.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  • {ptype}: {count} projects")
            lines.append("")
        
        # Recent patterns
        if context.recent_patterns:
            if context.recent_patterns.get("trending_up"):
                lines.append(f"Currently exploring: {', '.join(context.recent_patterns['trending_up'])}")
            if context.recent_patterns.get("new_explorations"):
                lines.append(f"New technologies tried: {', '.join(context.recent_patterns['new_explorations'])}")
        
        return "\n".join(lines)
    
    async def get_stack_confidence(
        self,
        stack_id: str,
        user_id: Optional[int] = None,
    ) -> float:
        """
        Calculate confidence score for recommending a stack.
        
        This combines global success rates with user-specific patterns
        to produce a confidence score (0.0-1.0).
        
        Args:
            stack_id: Stack to evaluate
            user_id: Optional user ID for personalization
            
        Returns:
            Confidence score (0.0-1.0)
        """
        try:
            # Get global success rate for stack
            stats = await self.dataforge.get_stack_success_rate(stack_id)
            
            if not stats:
                # Unknown stack, low confidence
                return 0.3
            
            # Base confidence from global success rate
            global_rate = stats.get("success_rate", 0.5)
            total_uses = stats.get("total_uses", 0)
            
            # Weight by number of uses (more data = higher confidence)
            use_weight = min(total_uses / 100.0, 1.0)  # Cap at 100 uses
            
            base_confidence = global_rate * 0.7 + use_weight * 0.3
            
            # If we have user-specific data, adjust confidence
            if user_id:
                context = await self.build_context(user_id)
                
                # Check if user has experience with this stack
                user_exp = next((s for s in context.successful_stacks if s.stack_id == stack_id), None)
                
                if user_exp:
                    # User has experience, weight heavily towards their success rate
                    user_confidence = user_exp.success_rate * 0.8 + base_confidence * 0.2
                    return user_confidence
            
            return base_confidence
        
        except Exception as e:
            logger.error(f"Error calculating stack confidence: {e}")
            return 0.5  # Default to neutral confidence


# Singleton instance
_context_service: Optional[ExperienceContextService] = None


def get_experience_service() -> ExperienceContextService:
    """
    Get or create the global ExperienceContextService instance.
    
    Returns:
        ExperienceContextService singleton
    """
    global _context_service
    if _context_service is None:
        _context_service = ExperienceContextService()
    return _context_service
