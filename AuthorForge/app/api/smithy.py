"""Smithy Brainstorming API - Genre-aware story idea generation and expansion"""

import logging
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import anthropic

from app.config import ANTHROPIC_API_KEY
from app.models.genres import Genre, Subgenre, GENRE_CONFIGS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/smithy", tags=["smithy"])


# Request/Response Models
class BrainstormRequest(BaseModel):
    """Request for story idea brainstorming"""
    prompt: str = Field(..., description="Creative prompt or seed idea")
    genre: Genre = Field(..., description="Fiction genre")
    subgenre: Optional[Subgenre] = Field(None, description="Specific subgenre")
    context: Optional[str] = Field(None, description="Additional context or constraints")
    num_ideas: int = Field(5, ge=1, le=10, description="Number of ideas to generate")


class StoryIdea(BaseModel):
    """A generated story idea"""
    title: str
    description: str
    themes: List[str]

    # Genre-specific fields (conditionally populated)
    magic_system: Optional[str] = None
    technology: Optional[str] = None
    biblical_connections: Optional[List[str]] = None

    worldbuilding_notes: Optional[str] = None
    character_hooks: Optional[List[str]] = None


class BrainstormResponse(BaseModel):
    """Response with generated story ideas"""
    prompt: str
    genre: Genre
    subgenre: Optional[Subgenre]
    ideas: List[StoryIdea]


class ExpandRequest(BaseModel):
    """Request to expand a story idea"""
    idea_title: str = Field(..., description="Story idea title")
    idea_description: str = Field(..., description="Story idea description")
    genre: Genre = Field(..., description="Fiction genre")
    aspect: str = Field(..., description="Aspect to expand: character, plot, worldbuilding, themes, magic, technology, spiritual")


class ExpandResponse(BaseModel):
    """Response with expanded story aspect"""
    aspect: str
    genre: Genre
    expansion: Dict[str, Any]


@router.post("/brainstorm", response_model=BrainstormResponse)
async def brainstorm_ideas(request: BrainstormRequest):
    """
    Generate story ideas using Claude AI.

    Supports genre-specific brainstorming for Fantasy, Sci-Fi, and Christian Fiction.

    Each genre produces ideas with appropriate elements:
    - Fantasy: magic systems, worldbuilding, mythology
    - Sci-Fi: technology, scientific concepts, future societies
    - Christian Fiction: biblical themes, spiritual journeys, faith elements
    """

    # Get genre configuration
    genre_config = GENRE_CONFIGS.get(request.genre)
    if not genre_config:
        raise HTTPException(status_code=400, detail=f"Unknown genre: {request.genre}")

    logger.info(f"Brainstorm request: '{request.prompt}' (genre: {request.genre}, num: {request.num_ideas})")

    # Build genre-specific instructions
    genre_specific_instructions = ""

    if request.genre == Genre.FANTASY:
        genre_specific_instructions = """
For each idea, include:
- "magic_system": A unique magic system or supernatural element (string)
- "worldbuilding_notes": Key world elements like cultures, geography, history (string)
- "character_hooks": Array of character concepts [protagonist hook, antagonist hook]
- "themes": Array of thematic elements to explore"""

    elif request.genre == Genre.SCIFI:
        genre_specific_instructions = """
For each idea, include:
- "technology": Central technology or scientific concept (string)
- "worldbuilding_notes": Future/alien setting details, societal structure (string)
- "character_hooks": Array of character concepts [protagonist hook, antagonist hook]
- "themes": Array of thematic elements about humanity, progress, ethics"""

    elif request.genre == Genre.CHRISTIAN_FICTION:
        genre_specific_instructions = """
For each idea, include:
- "biblical_connections": Array of biblical themes, scriptures, or parallels
- "worldbuilding_notes": Setting and context for the spiritual journey (string)
- "character_hooks": Array of character spiritual starting points
- "themes": Array of spiritual/faith themes to explore"""

    else:  # GENERAL
        genre_specific_instructions = """
For each idea, include:
- "worldbuilding_notes": Setting and context details (string)
- "character_hooks": Array of character concepts
- "themes": Array of thematic elements"""

    # Subgenre-specific guidance
    subgenre_note = ""
    if request.subgenre:
        subgenre_note = f"\nSubgenre focus: {request.subgenre.value.replace('_', ' ').title()}"

    # Build the prompt for Claude
    user_prompt = f"""Generate {request.num_ideas} compelling, original story ideas for {request.genre.value.replace('_', ' ')} fiction.

Seed Prompt: {request.prompt}
{f"Additional Context: {request.context}" if request.context else ""}
{subgenre_note}

{genre_specific_instructions}

Return ONLY a valid JSON array (no markdown formatting) with this exact structure:
[
  {{
    "title": "Compelling Story Title",
    "description": "2-3 sentence premise that hooks the reader",
    "themes": ["theme1", "theme2", "theme3"],
    {'"magic_system"' if request.genre == Genre.FANTASY else '"technology"' if request.genre == Genre.SCIFI else '"biblical_connections"'}: {"..." if request.genre != Genre.CHRISTIAN_FICTION else '["connection1", "connection2"]'},
    "worldbuilding_notes": "Key setting and world elements",
    "character_hooks": ["protagonist concept", "antagonist concept"]
  }}
]

Requirements:
- Each idea must be distinct and original
- Descriptions should be vivid and specific
- Include genre-appropriate elements
- Make ideas compelling and story-worthy
- Ensure diversity across all {request.num_ideas} ideas"""

    # Call Claude
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=genre_config.brainstorm_system_prompt,
            messages=[{
                "role": "user",
                "content": user_prompt
            }]
        )

        response_text = message.content[0].text
        logger.info("Received response from Claude")

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error(f"Error calling Claude: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate ideas: {str(e)}")

    # Parse response (handle markdown wrapping)
    try:
        # Remove markdown code blocks if present
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        ideas_data = json.loads(response_text)
        logger.info(f"Successfully parsed {len(ideas_data)} ideas")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.error(f"Response text: {response_text[:500]}")
        raise HTTPException(
            status_code=500,
            detail="Failed to parse AI response. Please try again."
        )

    # Convert to StoryIdea objects
    ideas = []
    for i, idea_data in enumerate(ideas_data[:request.num_ideas]):
        try:
            idea = StoryIdea(
                title=idea_data.get("title", f"Untitled Idea {i+1}"),
                description=idea_data.get("description", ""),
                themes=idea_data.get("themes", []),
                worldbuilding_notes=idea_data.get("worldbuilding_notes"),
                character_hooks=idea_data.get("character_hooks", [])
            )

            # Genre-specific fields
            if request.genre == Genre.FANTASY:
                idea.magic_system = idea_data.get("magic_system")
            elif request.genre == Genre.SCIFI:
                idea.technology = idea_data.get("technology")
            elif request.genre == Genre.CHRISTIAN_FICTION:
                idea.biblical_connections = idea_data.get("biblical_connections", [])

            ideas.append(idea)

        except Exception as e:
            logger.warning(f"Error parsing idea {i+1}: {e}")
            continue

    if not ideas:
        raise HTTPException(status_code=500, detail="Failed to generate valid ideas")

    logger.info(f"Generated {len(ideas)} valid story ideas")

    return BrainstormResponse(
        prompt=request.prompt,
        genre=request.genre,
        subgenre=request.subgenre,
        ideas=ideas
    )


@router.post("/expand", response_model=ExpandResponse)
async def expand_idea(request: ExpandRequest):
    """
    Expand a story idea into detailed components.

    Available aspects:
    - character: Detailed character profiles and arcs
    - plot: Three-act structure and plot beats
    - worldbuilding: World details, cultures, settings
    - themes: Thematic exploration and symbolism
    - magic: Magic system design (Fantasy only)
    - technology: Technology/science details (Sci-Fi only)
    - spiritual: Spiritual journey arc (Christian Fiction only)
    """

    genre_config = GENRE_CONFIGS.get(request.genre)
    if not genre_config:
        raise HTTPException(status_code=400, detail=f"Unknown genre: {request.genre}")

    logger.info(f"Expand request: '{request.idea_title}' - aspect: {request.aspect}, genre: {request.genre}")

    # Define aspect-specific prompts
    aspect_prompts = {
        "character": """Develop detailed character profiles in JSON format:
{
  "protagonist": {
    "name_concept": "...",
    "motivation": "...",
    "internal_conflict": "...",
    "external_conflict": "...",
    "character_arc": "...",
    "key_traits": ["trait1", "trait2", "trait3"],
    "flaws": ["flaw1", "flaw2"]
  },
  "antagonist": {
    "name_concept": "...",
    "motivation": "...",
    "why_they_oppose": "...",
    "complexity": "..."
  },
  "supporting_characters": [
    {
      "role": "...",
      "purpose": "...",
      "relationship_to_protagonist": "..."
    }
  ]
}""",

        "plot": """Create a detailed plot structure in JSON format:
{
  "act_one": {
    "opening_hook": "...",
    "inciting_incident": "...",
    "first_plot_point": "..."
  },
  "act_two": {
    "rising_action": ["beat1", "beat2", "beat3"],
    "midpoint_twist": "...",
    "complications": ["complication1", "complication2"],
    "low_point": "..."
  },
  "act_three": {
    "climax": "...",
    "resolution": "...",
    "thematic_payoff": "..."
  },
  "subplots": [
    {
      "description": "...",
      "how_it_weaves": "..."
    }
  ]
}""",

        "worldbuilding": """Develop comprehensive worldbuilding in JSON format:
{
  "setting": {
    "primary_location": "...",
    "geography": "...",
    "climate_atmosphere": "..."
  },
  "cultures": [
    {
      "name": "...",
      "values": "...",
      "governance": "...",
      "unique_elements": "..."
    }
  ],
  "history": {
    "key_events": ["event1", "event2"],
    "how_it_shapes_present": "..."
  },
  "daily_life": {
    "economy": "...",
    "social_structure": "...",
    "unique_customs": ["custom1", "custom2"]
  },
  "sensory_details": {
    "sights": "...",
    "sounds": "...",
    "unique_atmosphere": "..."
  }
}""",

        "themes": """Explore thematic depth in JSON format:
{
  "central_theme": {
    "statement": "...",
    "question_posed": "...",
    "how_characters_explore": "..."
  },
  "sub_themes": [
    {
      "theme": "...",
      "how_it_supports_main": "..."
    }
  ],
  "symbolic_elements": [
    {
      "symbol": "...",
      "meaning": "...",
      "when_it_appears": "..."
    }
  ],
  "character_perspectives": [
    {
      "character": "...",
      "their_view_on_theme": "..."
    }
  ],
  "thematic_resolution": "..."
}"""
    }

    # Genre-specific aspects
    if request.genre == Genre.FANTASY and request.aspect == "magic":
        aspect_prompts["magic"] = """Design a detailed magic system in JSON format:
{
  "source": "Where magic comes from",
  "rules": ["rule1", "rule2", "rule3"],
  "limitations": ["limitation1", "limitation2"],
  "costs": "What using magic costs the user",
  "who_can_use": "Who has access and how it's learned",
  "societal_impact": "How magic affects culture and society",
  "plot_implications": "How this magic system creates conflict",
  "unique_elements": "What makes this magic system distinctive"
}"""

    if request.genre == Genre.SCIFI and request.aspect == "technology":
        aspect_prompts["technology"] = """Design detailed technology/science in JSON format:
{
  "core_concept": "Central technological or scientific principle",
  "how_it_works": "Plausible mechanism and explanation",
  "limitations": ["limitation1", "limitation2"],
  "societal_changes": "How this tech transformed society",
  "ethical_implications": ["implication1", "implication2"],
  "conflict_generation": "How this creates story conflict",
  "unintended_consequences": "Dangers or unexpected effects",
  "current_status": "State of this tech in the story timeline"
}"""

    if request.genre == Genre.CHRISTIAN_FICTION and request.aspect == "spiritual":
        aspect_prompts["spiritual"] = """Develop the spiritual dimension in JSON format:
{
  "starting_point": {
    "faith_status": "Character's initial spiritual state",
    "relationship_with_god": "...",
    "beliefs_doubts": ["belief/doubt1", "belief/doubt2"]
  },
  "spiritual_challenges": [
    {
      "challenge": "...",
      "how_it_tests_faith": "..."
    }
  ],
  "biblical_parallels": [
    {
      "scripture_story": "...",
      "how_it_connects": "...",
      "verses": ["verse1", "verse2"]
    }
  ],
  "transformation_arc": {
    "key_moments": ["moment1", "moment2", "moment3"],
    "what_changes": "...",
    "spiritual_breakthrough": "..."
  },
  "faith_and_plot": "How spiritual growth connects to external story",
  "thematic_truth": "Spiritual truth the story explores"
}"""

    # Validate aspect
    if request.aspect not in aspect_prompts:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown aspect: {request.aspect}. Valid aspects: {', '.join(aspect_prompts.keys())}"
        )

    # Build prompt for Claude
    user_prompt = f"""Expand the following {request.genre.value.replace('_', ' ')} story idea.
Focus on: {request.aspect}

Story Idea:
Title: {request.idea_title}
Description: {request.idea_description}

{aspect_prompts[request.aspect]}

Return ONLY valid JSON (no markdown formatting) with detailed, specific content.
Be creative and ensure everything aligns with {request.genre.value.replace('_', ' ')} genre conventions."""

    # Call Claude
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=genre_config.brainstorm_system_prompt,
            messages=[{
                "role": "user",
                "content": user_prompt
            }]
        )

        response_text = message.content[0].text
        logger.info("Received expansion from Claude")

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error(f"Error calling Claude: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to expand idea: {str(e)}")

    # Parse response
    try:
        # Remove markdown code blocks if present
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        expansion_data = json.loads(response_text)
        logger.info("Successfully parsed expansion")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse expansion as JSON: {e}")
        # Return as structured text if JSON parsing fails
        expansion_data = {
            "expansion_text": response_text,
            "note": "Expansion provided as text (JSON parsing failed)"
        }

    return ExpandResponse(
        aspect=request.aspect,
        genre=request.genre,
        expansion=expansion_data
    )
