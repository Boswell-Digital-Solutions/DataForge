"""Research Assistant API - Genre-aware knowledge base queries with AI synthesis"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx
import anthropic

from app.config import DATAFORGE_URL, ANTHROPIC_API_KEY
from app.models.genres import Genre, GENRE_CONFIGS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


# Request/Response Models
class ResearchRequest(BaseModel):
    """Request for research query"""
    query: str = Field(..., description="Question to research")
    genre: Genre = Field(Genre.GENERAL, description="Fiction genre context")
    domain_id: Optional[str] = Field(None, description="Specific DataForge domain to search")
    max_results: int = Field(5, ge=1, le=20, description="Maximum number of sources to retrieve")


class Source(BaseModel):
    """Source document from knowledge base"""
    content: str
    document_title: str
    similarity_score: float


class ResearchResponse(BaseModel):
    """Response with AI-synthesized answer and sources"""
    query: str
    genre: Genre
    answer: str
    sources: List[Source]


@router.post("/query", response_model=ResearchResponse)
async def research_query(request: ResearchRequest):
    """
    Answer writing craft questions using DataForge knowledge base + Claude AI synthesis.

    Supports genre-specific research for Fantasy, Sci-Fi, and Christian Fiction.

    Flow:
    1. Query DataForge semantic search across relevant domains
    2. Retrieve top matching sources
    3. Synthesize answer using Claude with genre-appropriate context
    4. Return answer with source citations
    """

    # Get genre configuration
    genre_config = GENRE_CONFIGS.get(request.genre)
    if not genre_config:
        raise HTTPException(status_code=400, detail=f"Unknown genre: {request.genre}")

    logger.info(f"Research query: '{request.query}' (genre: {request.genre})")

    # Determine which domains to search
    domains_to_search = genre_config.knowledge_domains

    # If specific domain requested, use that instead
    if request.domain_id:
        domains_to_search = [request.domain_id]
        logger.info(f"Using specific domain: {request.domain_id}")
    else:
        logger.info(f"Searching domains: {domains_to_search}")

    # Step 1: Query DataForge for relevant sources
    all_sources = []
    async with httpx.AsyncClient() as client:
        for domain in domains_to_search:
            try:
                response = await client.post(
                    f"{DATAFORGE_URL}/api/search",
                    json={
                        "query": request.query,
                        "domain_id": domain,
                        "limit": request.max_results
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    all_sources.extend(results)
                    logger.info(f"Retrieved {len(results)} sources from domain '{domain}'")
                else:
                    logger.warning(f"DataForge query failed for domain '{domain}': {response.status_code}")
            except httpx.TimeoutException:
                logger.error(f"Timeout querying domain '{domain}'")
            except Exception as e:
                logger.error(f"Error querying domain '{domain}': {e}")

    # Sort by similarity and take top results
    all_sources.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
    top_sources = all_sources[:request.max_results]

    logger.info(f"Total sources retrieved: {len(top_sources)}")

    # Step 2: Handle no results case
    if not top_sources:
        logger.warning("No sources found in DataForge")
        return ResearchResponse(
            query=request.query,
            genre=request.genre,
            answer="I couldn't find relevant information in the knowledge base for this question. "
                   "This might mean:\n"
                   "1. No content has been added to DataForge yet\n"
                   "2. The question is outside the current knowledge base scope\n"
                   "3. Try rephrasing your question or using different keywords\n\n"
                   f"Searched domains: {', '.join(domains_to_search)}",
            sources=[]
        )

    # Step 3: Build context from sources
    context = "\n\n".join([
        f"Source {i+1} (from '{src['document_title']}', similarity: {src['similarity_score']:.2f}):\n{src['content']}"
        for i, src in enumerate(top_sources)
    ])

    logger.info(f"Built context from {len(top_sources)} sources")

    # Step 4: Synthesize answer using Claude with genre-specific prompt
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        user_prompt = f"""Based on the following sources from the knowledge base, answer this question:

Question: {request.query}

Sources:
{context}

Provide a comprehensive answer that:
1. Synthesizes information from the sources
2. Cites sources by number (e.g., "According to Source 1...")
3. Provides actionable advice for {request.genre.value.replace('_', ' ')} writers
4. Maintains the tone and focus appropriate for {request.genre.value.replace('_', ' ')} fiction
5. Includes specific examples where possible

Answer:"""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            system=genre_config.research_system_prompt,
            messages=[{
                "role": "user",
                "content": user_prompt
            }]
        )

        answer = message.content[0].text
        logger.info("Successfully synthesized answer with Claude")

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error(f"Error synthesizing answer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")

    # Step 5: Format sources for response
    formatted_sources = [
        Source(
            content=src["content"],
            document_title=src["document_title"],
            similarity_score=src["similarity_score"]
        )
        for src in top_sources
    ]

    return ResearchResponse(
        query=request.query,
        genre=request.genre,
        answer=answer,
        sources=formatted_sources
    )


@router.get("/domains")
async def get_available_domains():
    """Get available DataForge domains for each genre"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DATAFORGE_URL}/api/search/stats",
                timeout=5.0
            )
            if response.status_code == 200:
                stats = response.json()
                return {
                    "dataforge_domains": stats.get("domains", []),
                    "genre_mappings": {
                        genre.value: config.knowledge_domains
                        for genre, config in GENRE_CONFIGS.items()
                    }
                }
    except Exception as e:
        logger.error(f"Error fetching domains: {e}")

    # Fallback to configuration
    return {
        "genre_mappings": {
            genre.value: config.knowledge_domains
            for genre, config in GENRE_CONFIGS.items()
        }
    }
