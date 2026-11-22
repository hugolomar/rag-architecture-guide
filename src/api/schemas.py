"""FastAPI boundary schemas matching OpenAPI 3.1 contract source of truth."""

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import BehaviorEnum
from src.domain.queries import Citation


class QueryRequest(BaseModel):
    """Inbound query request contract."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural language user inquiry.",
        examples=["Which awslogs options configure CloudWatch region and log group?"],
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of evidence chunks to retrieve.",
        examples=[3],
    )

    model_config = ConfigDict(extra="forbid")


class QueryResponse(BaseModel):
    """Outbound query response contract."""

    answer: str = Field(..., description="Synthesized answer text or governed explanation.")
    behavior: BehaviorEnum = Field(..., description="Governed classification of the response.")
    citations: list[Citation] = Field(
        ..., description="List of source citations (empty for refusals)."
    )
    trace_id: str = Field(..., description="Distributed OpenTelemetry trace identifier.")
    latency_ms: float = Field(
        ..., ge=0.0, description="Total request execution latency in milliseconds."
    )

    model_config = ConfigDict(extra="forbid")


class ErrorResponse(BaseModel):
    """Standard HTTP error response payload."""

    detail: str = Field(..., description="Actionable description of the error.")
    error_code: str = Field(..., description="Domain or transport error code.")

    model_config = ConfigDict(extra="forbid")

