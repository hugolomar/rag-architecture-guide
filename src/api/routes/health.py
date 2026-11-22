"""Health and readiness check endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/healthz", summary="Liveness and readiness probe")
def healthcheck() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}

