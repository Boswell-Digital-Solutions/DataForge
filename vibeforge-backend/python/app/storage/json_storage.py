import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

# Data directory for JSON persistence
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RUNS_FILE = DATA_DIR / "runs.json"
CONTEXTS_FILE = DATA_DIR / "contexts.json"
EVALUATIONS_FILE = DATA_DIR / "evaluations.json"


def _load_json(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSON file, return empty list if not exists."""
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_json(file_path: Path, data: List[Dict[str, Any]]) -> None:
    """Save data to JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ============================================================================
# Runs Storage
# ============================================================================


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a run by ID."""
    runs = _load_json(RUNS_FILE)
    for run in runs:
        if run["id"] == run_id:
            return run
    return None


def create_run(
    workspace_id: str,
    model: str,
    prompt: str,
    context_ids: Optional[List[str]] = None,
    model_config: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a new run."""
    import uuid

    run = {
        "id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "model": model,
        "prompt": prompt,
        "status": "pending",
        "output": None,
        "error": None,
        "tokens_used": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "duration_ms": None,
        "context_ids": context_ids or [],
        "model_config": model_config or {},
        "tags": tags or [],
    }

    runs = _load_json(RUNS_FILE)
    runs.append(run)
    _save_json(RUNS_FILE, runs)

    return run


def update_run(run_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a run by ID."""
    runs = _load_json(RUNS_FILE)
    for i, run in enumerate(runs):
        if run["id"] == run_id:
            runs[i].update(updates)
            _save_json(RUNS_FILE, runs)
            return runs[i]
    return None


def list_runs(
    workspace_id: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """List runs with optional filters."""
    runs = _load_json(RUNS_FILE)

    # Filter
    if workspace_id:
        runs = [r for r in runs if r["workspace_id"] == workspace_id]
    if model:
        runs = [r for r in runs if r["model"] == model]
    if status:
        runs = [r for r in runs if r["status"] == status]

    # Sort by created_at descending
    runs.sort(key=lambda x: x["created_at"], reverse=True)

    total = len(runs)
    paginated = runs[offset : offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": paginated,
    }


# ============================================================================
# Contexts Storage
# ============================================================================


def get_context(context_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a context by ID."""
    contexts = _load_json(CONTEXTS_FILE)
    for ctx in contexts:
        if ctx["id"] == context_id:
            return ctx
    return None


def create_context(
    workspace_id: str,
    title: str,
    kind: str,
    description: str,
    content: str,
    tags: Optional[List[str]] = None,
    source: str = "local",
) -> Dict[str, Any]:
    """Create a new context block."""
    import uuid

    context = {
        "id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "title": title,
        "kind": kind,
        "description": description,
        "content": content,
        "tags": tags or [],
        "is_active": False,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }

    contexts = _load_json(CONTEXTS_FILE)
    contexts.append(context)
    _save_json(CONTEXTS_FILE, contexts)

    return context


def list_contexts(
    workspace_id: Optional[str] = None,
    kind: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """List contexts with optional filters."""
    contexts = _load_json(CONTEXTS_FILE)

    if workspace_id:
        contexts = [c for c in contexts if c.get("workspace_id") == workspace_id]
    if kind:
        contexts = [c for c in contexts if c["kind"] == kind]
    if is_active is not None:
        contexts = [c for c in contexts if c["is_active"] == is_active]

    contexts.sort(key=lambda x: x["last_updated"], reverse=True)
    return contexts


def toggle_context_active(context_id: str) -> Optional[Dict[str, Any]]:
    """Toggle the active status of a context."""
    contexts = _load_json(CONTEXTS_FILE)
    for i, ctx in enumerate(contexts):
        if ctx["id"] == context_id:
            contexts[i]["is_active"] = not contexts[i]["is_active"]
            contexts[i]["last_updated"] = datetime.now(timezone.utc).isoformat()
            _save_json(CONTEXTS_FILE, contexts)
            return contexts[i]
    return None


# ============================================================================
# Evaluations Storage
# ============================================================================


def create_evaluation(
    run_id: str,
    evaluator: str,
    scores: Optional[Dict[str, float]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    """Create a new evaluation."""
    import uuid

    evaluation = {
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "evaluator": evaluator,
        "scores": scores or {},
        "notes": notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    evals = _load_json(EVALUATIONS_FILE)
    evals.append(evaluation)
    _save_json(EVALUATIONS_FILE, evals)

    return evaluation


def list_evaluations(run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List evaluations with optional run_id filter."""
    evals = _load_json(EVALUATIONS_FILE)

    if run_id:
        evals = [e for e in evals if e["run_id"] == run_id]

    evals.sort(key=lambda x: x["created_at"], reverse=True)
    return evals
