"""NeuroForge API router (stub)."""

from fastapi import APIRouter
from typing import List
from app.models import EvaluationModel, SweepConfigModel

router = APIRouter(prefix="/v1/neuroforge", tags=["NeuroForge"])


@router.post("/eval", response_model=EvaluationModel, status_code=201)
async def create_evaluation(
    run_id: str, evaluator: str, scores: dict, notes: str = ""
):
    """Create an evaluation for a run."""
    from datetime import datetime, timezone
    import uuid

    eval_obj = {
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "evaluator": evaluator,
        "scores": scores,
        "notes": notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return EvaluationModel(**eval_obj)


@router.get("/evals", response_model=List[EvaluationModel])
async def list_evaluations(run_id: str = None):
    """List evaluations with optional run_id filter."""
    return []


@router.post("/sweep", response_model=SweepConfigModel, status_code=201)
async def create_sweep(name: str, parameters: dict):
    """Create a hyperparameter sweep configuration."""
    from datetime import datetime, timezone
    import uuid

    sweep = {
        "id": str(uuid.uuid4()),
        "name": name,
        "parameters": parameters,
        "total_runs": 1,  # Calculate from grid
        "completed_runs": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return SweepConfigModel(**sweep)


@router.get("/sweep/{sweep_id}", response_model=SweepConfigModel)
async def get_sweep(sweep_id: str):
    """Get sweep status and results."""
    from datetime import datetime, timezone

    return SweepConfigModel(
        id=sweep_id,
        name="stub",
        parameters={},
        total_runs=0,
        completed_runs=0,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
