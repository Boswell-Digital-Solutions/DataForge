"""JSON file-based repository for model runs."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class RunsFileRepo:
    """Repository for persisting runs to JSON files."""

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the repository.

        Args:
            data_dir: Directory to store JSON files (default: app/data/)
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.runs_file = self.data_dir / "runs.json"

        logger.info(f"RunsFileRepo initialized at {self.runs_file}")

    def _load_runs(self) -> List[Dict[str, Any]]:
        """Load all runs from JSON file."""
        if not self.runs_file.exists():
            return []

        try:
            with open(self.runs_file, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading runs file: {e}")
            return []

    def _save_runs(self, runs: List[Dict[str, Any]]) -> None:
        """Save runs to JSON file."""
        try:
            with open(self.runs_file, "w") as f:
                json.dump(runs, f, indent=2, default=str)
            logger.debug(f"Saved {len(runs)} runs to {self.runs_file}")
        except IOError as e:
            logger.error(f"Error saving runs file: {e}")
            raise

    def create_run(
        self,
        model: str,
        prompt: str,
        status: str,
        active_contexts: Optional[List[Dict[str, Any]]] = None,
        data_profile_id: Optional[str] = None,
        eval_profile_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new run record.

        Args:
            model: Model identifier
            prompt: The prompt text
            status: Initial status (should be "pending")
            active_contexts: List of context blocks
            data_profile_id: Optional data profile ID
            eval_profile_id: Optional eval profile ID

        Returns:
            The created run record with ID
        """
        run_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        run = {
            "id": run_id,
            "model": model,
            "prompt": prompt,
            "status": status,
            "output": None,
            "error": None,
            "tokens_used": None,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "duration_ms": None,
            "active_contexts": active_contexts or [],
            "data_profile_id": data_profile_id,
            "eval_profile_id": eval_profile_id,
        }

        runs = self._load_runs()
        runs.append(run)
        self._save_runs(runs)

        logger.info(f"Created run {run_id} for model {model}")
        return run

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a run by ID.

        Args:
            run_id: The run ID

        Returns:
            The run record, or None if not found
        """
        runs = self._load_runs()
        for run in runs:
            if run.get("id") == run_id:
                return run
        return None

    def update_run(
        self,
        run_id: str,
        output: Optional[str] = None,
        error: Optional[str] = None,
        status: Optional[str] = None,
        tokens_used: Optional[Dict[str, int]] = None,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a run record.

        Args:
            run_id: The run ID
            output: Completion output text
            error: Error message if applicable
            status: Updated status
            tokens_used: Token usage dict with prompt_tokens, completion_tokens, total_tokens
            started_at: ISO timestamp when run started
            completed_at: ISO timestamp when run completed
            duration_ms: Duration in milliseconds

        Returns:
            The updated run record, or None if not found
        """
        runs = self._load_runs()
        for run in runs:
            if run.get("id") == run_id:
                if output is not None:
                    run["output"] = output
                if error is not None:
                    run["error"] = error
                if status is not None:
                    run["status"] = status
                if tokens_used is not None:
                    run["tokens_used"] = tokens_used
                if started_at is not None:
                    run["started_at"] = started_at
                if completed_at is not None:
                    run["completed_at"] = completed_at
                if duration_ms is not None:
                    run["duration_ms"] = duration_ms

                self._save_runs(runs)
                logger.info(f"Updated run {run_id}")
                return run

        logger.warning(f"Run {run_id} not found for update")
        return None

    def list_runs(
        self,
        limit: int = 10,
        offset: int = 0,
        model: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List runs with optional filtering and pagination.

        Args:
            limit: Max number of results
            offset: Number of results to skip
            model: Filter by model (optional)
            status: Filter by status (optional)

        Returns:
            Dict with total, limit, offset, and items list
        """
        runs = self._load_runs()

        # Filter
        filtered_runs = runs
        if model:
            filtered_runs = [r for r in filtered_runs if r.get("model") == model]
        if status:
            filtered_runs = [r for r in filtered_runs if r.get("status") == status]

        # Sort by created_at descending
        sorted_runs = sorted(
            filtered_runs,
            key=lambda r: r.get("created_at", ""),
            reverse=True,
        )

        total = len(sorted_runs)
        paginated = sorted_runs[offset : offset + limit]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": paginated,
        }

    def delete_run(self, run_id: str) -> bool:
        """
        Delete a run record.

        Args:
            run_id: The run ID

        Returns:
            True if deleted, False if not found
        """
        runs = self._load_runs()
        original_count = len(runs)
        runs = [r for r in runs if r.get("id") != run_id]

        if len(runs) < original_count:
            self._save_runs(runs)
            logger.info(f"Deleted run {run_id}")
            return True

        logger.warning(f"Run {run_id} not found for deletion")
        return False


# ============================================================================
# Global Repository Instance
# ============================================================================

_runs_repo_instance: Optional[RunsFileRepo] = None


def get_runs_repo(data_dir: Optional[Path] = None) -> RunsFileRepo:
    """Get or create the global runs repository instance."""
    global _runs_repo_instance
    if _runs_repo_instance is None:
        _runs_repo_instance = RunsFileRepo(data_dir)
    return _runs_repo_instance
