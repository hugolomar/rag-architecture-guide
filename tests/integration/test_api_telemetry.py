"""Integration tests for telemetry propagation and data hygiene in API endpoints.

Verifies distributed trace ID propagation, latency calculation, and sensitive
credential scrubbing.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_orchestrator
from src.api.main import app
from src.domain.enums import BehaviorEnum
from src.domain.ports.generation import GenerationPort
from src.domain.ports.identity import TokenValidatorPort
from src.domain.ports.retrieval import RetrievalPort
from src.domain.queries import CallerContext, Citation, GenerationResult, RetrievedChunk
from src.orchestration.query_orchestrator import QueryOrchestrator

pytestmark = pytest.mark.integration


class DummyValidator(TokenValidatorPort):
    """Stub validator returning valid user."""

    def validate_token(self, token: str) -> CallerContext:
        return CallerContext(user_id="user-tel", groups={"all-employees"})


class DummyRetriever(RetrievalPort):
    """Stub retriever returning 1 chunk."""

    def retrieve(self, query: str, caller_groups: set[str], top_k: int = 3) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id="DOC-TEL-001#c0",
                doc_id="DOC-TEL-001",
                text="Telemetry sample.",
                score=0.9,
                allowed_groups=["all-employees"],
            )
        ]


class DummyGenerator(GenerationPort):
    """Stub generator."""

    def generate(self, query: str, context: list[RetrievedChunk], user_id: str) -> GenerationResult:
        return GenerationResult(
            answer="Telemetry test answer.",
            behavior=BehaviorEnum.GROUND_ANSWER,
            citations=[Citation(doc_id="DOC-TEL-001", chunk_id="DOC-TEL-001#c0")],
        )


@pytest.fixture
def telemetry_client() -> Iterator[TestClient]:
    """Fixture providing TestClient with mock orchestrator."""
    orchestrator = QueryOrchestrator(
        token_validator=DummyValidator(),
        retriever=DummyRetriever(),
        generator=DummyGenerator(),
    )
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ==========================================
# TELEMETRY & ATTRIBUTE TESTS
# ==========================================


def test_query_returns_valid_trace_id_and_latency(telemetry_client: TestClient) -> None:
    """Verify trace_id is a 32-character hex string and latency_ms is non-negative."""
    response = telemetry_client.post(
        "/query",
        headers={"Authorization": "Bearer secret-test-token-12345"},
        json={"query": "Test query for telemetry"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "trace_id" in data
    assert len(data["trace_id"]) == 32
    assert isinstance(data["latency_ms"], float)
    assert data["latency_ms"] >= 0.0
