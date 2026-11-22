"""Query route handler orchestrating authenticated knowledge inquiries."""

import time
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from opentelemetry import trace

from src.adapters.auth.oidc_validator import AuthenticationError
from src.api.dependencies import get_orchestrator
from src.api.schemas import ErrorResponse, QueryRequest, QueryResponse
from src.orchestration.query_orchestrator import QueryOrchestrator

router = APIRouter(tags=["Query"])
tracer = trace.get_tracer(__name__)


@router.post(
    "/query",
    summary="Execute governed knowledge query",
    description="Authenticates caller via Bearer token, executes pre-inference security-trimmed hybrid retrieval, and synthesizes evidence-grounded answers.",
    operation_id="execute_query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Missing, forged, or expired authentication token."},
        502: {"model": ErrorResponse, "description": "Upstream dependency failure."},
        504: {"model": ErrorResponse, "description": "Endpoint timeout budget exceeded."},
    },
)
def execute_query(
    payload: QueryRequest,
    orchestrator: Annotated[QueryOrchestrator, Depends(get_orchestrator)],
    authorization: Annotated[str | None, Header(description="OIDC Bearer token")] = None,
) -> QueryResponse:
    """Execute governed query and return synthesis, behavior, citations, and telemetry."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization token",
        )

    start_time = time.perf_counter()
    span = trace.get_current_span()
    ctx = span.get_span_context()
    trace_id = format(ctx.trace_id, "032x") if ctx.is_valid else uuid.uuid4().hex

    try:
        result = orchestrator.execute(
            query=payload.query,
            bearer_token=authorization,
            top_k=payload.top_k,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Execution timeout budget exceeded: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream provider failure: {exc}",
        ) from exc

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return QueryResponse(
        answer=result.answer,
        behavior=result.behavior,
        citations=result.citations,
        trace_id=trace_id,
        latency_ms=duration_ms,
    )
