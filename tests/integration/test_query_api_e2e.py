"""End-to-end integration tests for FastAPI Query API endpoints.

Verifies HTTP transport semantics, status codes (200, 401, 422), input
validation bounds, and response payload structures via TestClient.
"""

from collections.abc import Iterator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.dependencies import get_orchestrator
from src.api.main import app
from src.domain.enums import BehaviorEnum
from src.domain.exceptions import GenerationProviderError, RetrievalProviderError
from src.domain.ports.generation import GenerationPort
from src.domain.ports.identity import TokenValidatorPort
from src.domain.ports.retrieval import RetrievalPort
from src.domain.queries import CallerContext, Citation, GenerationResult, RetrievedChunk
from src.orchestration.query_orchestrator import QueryOrchestrator

pytestmark = pytest.mark.integration


# ==========================================
# TEST FIXTURES & DOUBLES
# ==========================================


class MockTestTokenValidator(TokenValidatorPort):
    """Stub validator for TestClient integration tests."""

    def validate_token(self, token: str) -> CallerContext:
        clean = token.replace("Bearer ", "").strip()
        if clean == "valid-eng-token":
            return CallerContext(user_id="user-eng", groups={"engineering-core", "all-employees"})
        if clean == "valid-hr-token":
            return CallerContext(user_id="user-hr", groups={"people-team", "all-employees"})
        from src.adapters.auth.oidc_validator import AuthenticationError

        raise AuthenticationError("Invalid test bearer token")


class MockTestRetriever(RetrievalPort):
    """Stub retriever returning engineering documents for engineering caller."""

    def retrieve(
        self,
        query: str,
        caller_groups: set[str],
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        if "engineering-core" in caller_groups and "deployment" in query.lower():
            return [
                RetrievedChunk(
                    chunk_id="DOC-ENG-001#c0",
                    doc_id="DOC-ENG-001",
                    text="Docker deployment standards and configurations.",
                    score=0.91,
                    allowed_groups=["engineering-core"],
                )
            ]
        return []


class MockTestGenerator(GenerationPort):
    """Stub generator for testing."""

    def generate(
        self,
        query: str,
        context: list[RetrievedChunk],
        user_id: str,
    ) -> GenerationResult:
        if not context:
            return GenerationResult(
                answer="No relevant documentation available.",
                behavior=BehaviorEnum.ABSTAIN,
                citations=[],
            )
        return GenerationResult(
            answer="Deployment is configured using standard compose files.",
            behavior=BehaviorEnum.GROUND_ANSWER,
            citations=[Citation(doc_id=context[0].doc_id, chunk_id=context[0].chunk_id)],
        )


@pytest.fixture
def test_client() -> Iterator[TestClient]:
    """Create a TestClient with wired dependency overrides."""
    orchestrator = QueryOrchestrator(
        token_validator=MockTestTokenValidator(),
        retriever=MockTestRetriever(),
        generator=MockTestGenerator(),
    )
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ==========================================
# END-TO-END HTTP TESTS
# ==========================================


def test_query_success_ground_answer(test_client: TestClient) -> None:
    """Verify 200 OK ground_answer response with valid token and relevant query."""
    response = test_client.post(
        "/query",
        headers={"Authorization": "Bearer valid-eng-token"},
        json={"query": "How is deployment configured?", "top_k": 3},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["behavior"] == "ground_answer"
    assert "Deployment" in data["answer"]
    assert len(data["citations"]) == 1
    assert data["citations"][0]["doc_id"] == "DOC-ENG-001"
    assert "trace_id" in data
    assert data["latency_ms"] >= 0.0


def test_query_unauthorized_missing_token(test_client: TestClient) -> None:
    """Verify 401 Unauthorized when Authorization header is absent."""
    response = test_client.post(
        "/query",
        json={"query": "Any question text here?"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Missing or invalid authorization token" in response.json()["detail"]


def test_query_unauthorized_invalid_token(test_client: TestClient) -> None:
    """Verify 401 Unauthorized when bearer token validation fails."""
    response = test_client.post(
        "/query",
        headers={"Authorization": "Bearer bad-token-xyz"},
        json={"query": "Valid question text here?"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_query_validation_error_too_short(test_client: TestClient) -> None:
    """Verify 422 Unprocessable Entity when query is shorter than 3 characters."""
    response = test_client.post(
        "/query",
        headers={"Authorization": "Bearer valid-eng-token"},
        json={"query": "hi"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_query_validation_error_top_k_out_of_bounds(test_client: TestClient) -> None:
    """Verify 422 Unprocessable Entity when top_k exceeds 10."""
    response = test_client.post(
        "/query",
        headers={"Authorization": "Bearer valid-eng-token"},
        json={"query": "Valid query text", "top_k": 15},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_healthz_endpoint(test_client: TestClient) -> None:
    """Verify GET /healthz liveness probe returns 200 OK."""
    response = test_client.get("/healthz")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_query_upstream_provider_failure_returns_502(test_client: TestClient) -> None:
    """Verify 502 Bad Gateway when an upstream dependency fails."""
    class FailingRetriever(RetrievalPort):
        def retrieve(self, query: str, caller_groups: set[str], top_k: int = 3) -> list[RetrievedChunk]:
            raise RetrievalProviderError("Qdrant connection dropped")

    class FailingGenerator(GenerationPort):
        def generate(self, query: str, context: list[RetrievedChunk], user_id: str) -> GenerationResult:
            raise GenerationProviderError("LiteLLM 503 Service Unavailable")

    # 1. Retrieval failure produces 502
    failing_orchestrator = QueryOrchestrator(
        token_validator=MockTestTokenValidator(),
        retriever=FailingRetriever(),
        generator=MockTestGenerator(),
    )
    app.dependency_overrides[get_orchestrator] = lambda: failing_orchestrator
    try:
        response = test_client.post(
            "/query",
            headers={"Authorization": "Bearer valid-eng-token"},
            json={"query": "How is deployment configured?", "top_k": 3},
        )
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Upstream provider failure" in response.json()["detail"]
    finally:
        del app.dependency_overrides[get_orchestrator]

    # 2. Generation failure produces 502
    gen_failing_orchestrator = QueryOrchestrator(
        token_validator=MockTestTokenValidator(),
        retriever=MockTestRetriever(),
        generator=FailingGenerator(),
    )
    app.dependency_overrides[get_orchestrator] = lambda: gen_failing_orchestrator
    try:
        response = test_client.post(
            "/query",
            headers={"Authorization": "Bearer valid-eng-token"},
            json={"query": "How is deployment configured?", "top_k": 3},
        )
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Upstream provider failure" in response.json()["detail"]
    finally:
        del app.dependency_overrides[get_orchestrator]


def test_query_timeout_budget_exceeded_returns_504(test_client: TestClient) -> None:
    """Verify 504 Gateway Timeout when query execution exceeds timeout budget."""
    class TimingOutGenerator(GenerationPort):
        def generate(self, query: str, context: list[RetrievedChunk], user_id: str) -> GenerationResult:
            raise TimeoutError("Execution budget 2000ms exceeded")

    timeout_orchestrator = QueryOrchestrator(
        token_validator=MockTestTokenValidator(),
        retriever=MockTestRetriever(),
        generator=TimingOutGenerator(),
    )
    app.dependency_overrides[get_orchestrator] = lambda: timeout_orchestrator
    try:
        response = test_client.post(
            "/query",
            headers={"Authorization": "Bearer valid-eng-token"},
            json={"query": "How is deployment configured?", "top_k": 3},
        )
        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        assert "timeout budget exceeded" in response.json()["detail"]
    finally:
        del app.dependency_overrides[get_orchestrator]
