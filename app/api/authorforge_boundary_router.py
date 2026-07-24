"""Fail-closed tombstone for the retired AuthorForge cloud-content API."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/projects", tags=["authorforge-boundary"])

_DETAIL = {
    "code": "authorforge_content_local_only",
    "message": (
        "AuthorForge user content is owned exclusively by AuthorForge's embedded "
        "database; DataForge does not accept or serve it."
    ),
}


@router.api_route(
    "",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
@router.api_route(
    "/{retired_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
def reject_authorforge_content(retired_path: str = "") -> None:
    """Reject without parsing, inspecting, logging, or persisting a request body."""
    raise HTTPException(status_code=410, detail=_DETAIL)
