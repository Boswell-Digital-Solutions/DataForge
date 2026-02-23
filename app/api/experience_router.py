"""Experience Store API router for DataForge.

Provides endpoints for creating, searching, and retrieving execution
experience records used by the ForgeAgents agentic reasoning system.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agentic_reasoning_models import ExecutionExperienceModel
from app.models.agentic_reasoning_schemas import (
    ExperienceCreate,
    ExperienceResponse,
    ExperienceSearchRequest,
    ExperienceSearchResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/experience",
    tags=["Experience Store"],
)


def _experience_to_response(db_exp: ExecutionExperienceModel) -> ExperienceResponse:
    """Convert ORM model to response schema."""
    return ExperienceResponse(
        experience_id=db_exp.experience_id,
        run_id=db_exp.run_id,
        agent_id=db_exp.agent_id,
        agent_archetype=db_exp.agent_archetype,
        target_scope=db_exp.target_scope,
        execution_summary=db_exp.execution_summary,
        outcome=db_exp.outcome,
        gate_results_snapshot=db_exp.gate_results_snapshot,
        tool_sequence=db_exp.tool_sequence,
        duration_ms=db_exp.duration_ms,
        cost_usd=float(db_exp.cost_usd) if db_exp.cost_usd is not None else None,
        created_at=db_exp.created_at,
    )


@router.post(
    "",
    status_code=201,
    response_model=ExperienceResponse,
    summary="Create an execution experience record",
)
async def create_experience(
    experience: ExperienceCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Index a new execution outcome in the Experience Store.

    Called from the Reflect phase of the 5-phase execution loop after
    a completed execution (success or failure).
    """
    logger.info(f"Creating experience record for run {experience.run_id}")

    db_experience = ExecutionExperienceModel(
        run_id=experience.run_id,
        agent_id=experience.agent_id,
        agent_archetype=experience.agent_archetype,
        task_embedding=experience.task_embedding,
        target_scope=experience.target_scope,
        execution_summary=experience.execution_summary,
        outcome=experience.outcome.value,
        gate_results_snapshot=experience.gate_results_snapshot,
        tool_sequence=experience.tool_sequence,
        duration_ms=experience.duration_ms,
        cost_usd=experience.cost_usd,
    )

    db.add(db_experience)
    db.commit()
    db.refresh(db_experience)

    logger.info(f"Created experience {db_experience.experience_id} for run {experience.run_id}")

    return _experience_to_response(db_experience)


@router.post(
    "/search",
    response_model=list[ExperienceSearchResult],
    summary="Semantic search over execution experiences",
)
async def search_experiences(
    search: ExperienceSearchRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Search for relevant past execution experiences using cosine similarity.

    Used by the Plan phase to retrieve execution context before the
    LLM planning call. Returns results ordered by similarity descending.
    """
    logger.info(
        f"Searching experiences: archetype={search.agent_archetype}, "
        f"outcome={search.outcome}, min_sim={search.min_similarity}, limit={search.limit}"
    )

    # Build the cosine similarity query using pgvector
    embedding_str = "[" + ",".join(str(v) for v in search.query_embedding) + "]"

    # pgvector cosine distance: 1 - cosine_similarity
    # We want similarity >= min_similarity, so distance <= 1 - min_similarity
    max_distance = 1.0 - search.min_similarity

    filters = []
    params = {
        "embedding": embedding_str,
        "max_distance": max_distance,
        "limit": search.limit,
    }

    if search.agent_archetype:
        filters.append("agent_archetype = :archetype")
        params["archetype"] = search.agent_archetype

    if search.outcome:
        filters.append("outcome = :outcome")
        params["outcome"] = search.outcome.value

    where_clause = ""
    if filters:
        where_clause = "AND " + " AND ".join(filters)

    query = text(f"""
        SELECT
            experience_id, run_id, agent_id, agent_archetype,
            target_scope, execution_summary, outcome,
            gate_results_snapshot, tool_sequence, duration_ms, cost_usd,
            created_at,
            1 - (task_embedding <=> :embedding::vector) AS similarity
        FROM execution_experiences
        WHERE (task_embedding <=> :embedding::vector) <= :max_distance
        {where_clause}
        ORDER BY task_embedding <=> :embedding::vector ASC
        LIMIT :limit
    """)

    results = db.execute(query, params).fetchall()

    return [
        ExperienceSearchResult(
            experience_id=row.experience_id,
            run_id=row.run_id,
            agent_id=row.agent_id,
            agent_archetype=row.agent_archetype,
            target_scope=row.target_scope,
            execution_summary=row.execution_summary,
            outcome=row.outcome,
            gate_results_snapshot=row.gate_results_snapshot,
            tool_sequence=row.tool_sequence,
            duration_ms=row.duration_ms,
            cost_usd=float(row.cost_usd) if row.cost_usd is not None else None,
            created_at=row.created_at,
            similarity=float(row.similarity),
        )
        for row in results
    ]


@router.get(
    "/{experience_id}",
    response_model=ExperienceResponse,
    summary="Get a single experience record",
)
async def get_experience(
    experience_id: UUID,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Retrieve a single execution experience record by ID."""
    db_experience = db.query(ExecutionExperienceModel).filter(
        ExecutionExperienceModel.experience_id == experience_id
    ).first()

    if not db_experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    return _experience_to_response(db_experience)
