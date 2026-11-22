"""Unit tests for the query orchestrator application service.

Verifies end-to-end orchestration across authentication, security-trimmed
retrieval, grounded generation, and behavior resolution using mock ports.
"""

import pytest

from src.adapters.auth.oidc_validator import AuthenticationError
from src.domain.enums import BehaviorEnum
from src.domain.ports.generation import GenerationPort
from src.domain.ports.identity import TokenValidatorPort
from src.domain.ports.retrieval import RetrievalPort
from src.domain.queries import CallerContext, Citation, GenerationResult, RetrievedChunk

pytestmark = pytest.mark.unit


# ==========================================
# TEST DOUBLES FOR PORTS
# ==========================================


class StubTokenValidator(TokenValidatorPort):
    """Stub validator returning preconfigured caller context or raising."""

    def __init__(self, context: CallerContext | None = None, should_fail: bool = False) -> None:
        self.context = context or CallerContext(
            user_id="user-123",
            groups={"all-employees", "engineering-core"},
        )
        self.should_fail = should_fail

    def validate_token(self, token: str) -> CallerContext:
        if self.should_fail or not token:
            raise AuthenticationError("Invalid or missing token")
        return self.context


class StubRetrievalPort(RetrievalPort):
    """Stub retrieval returning controlled evidence chunks."""

    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self.chunks = chunks if chunks is not None else []
        self.last_caller_groups: set[str] | None = None

    def retrieve(
        self,
        query: str,
        caller_groups: set[str],
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        self.last_caller_groups = caller_groups
        return self.chunks[:top_k]


class StubGenerationPort(GenerationPort):
    """Stub generation returning controlled answers and behaviors."""

    def __init__(self, default_behavior: BehaviorEnum = BehaviorEnum.GROUND_ANSWER) -> None:
        self.default_behavior = default_behavior

    def generate(
        self,
        query: str,
        context: list[RetrievedChunk],
        user_id: str,
    ) -> GenerationResult:
        if not context:
            return GenerationResult(
                answer="No relevant evidence found.",
                behavior=BehaviorEnum.ABSTAIN,
                citations=[],
            )
        return GenerationResult(
            answer="Grounded synthesis based on evidence.",
            behavior=self.default_behavior,
            citations=[Citation(doc_id=c.doc_id, chunk_id=c.chunk_id) for c in context],
        )


# ==========================================
# ORCHESTRATION HAPPY PATH & BEHAVIORS
# ==========================================


def test_orchestrator_ground_answer_flow() -> None:
    """Verify standard happy path flow returning ground_answer with citations."""
    from src.orchestration.query_orchestrator import QueryOrchestrator

    chunk = RetrievedChunk(
        chunk_id="DOC-ENG-001#c0",
        doc_id="DOC-ENG-001",
        text="Docker deployment policy details.",
        score=0.95,
        allowed_groups=["engineering-core"],
    )

    validator = StubTokenValidator()
    retriever = StubRetrievalPort(chunks=[chunk])
    generator = StubGenerationPort(default_behavior=BehaviorEnum.GROUND_ANSWER)

    orchestrator = QueryOrchestrator(
        token_validator=validator,
        retriever=retriever,
        generator=generator,
    )

    result = orchestrator.execute(
        query="What is the deployment policy?",
        bearer_token="Bearer valid.token.here",
        top_k=3,
    )

    assert result.behavior == BehaviorEnum.GROUND_ANSWER
    assert len(result.citations) == 1
    assert result.citations[0].doc_id == "DOC-ENG-001"
    assert retriever.last_caller_groups == {"all-employees", "engineering-core"}


def test_orchestrator_abstain_on_empty_retrieval() -> None:
    """Verify orchestrator abstains when no evidence is returned."""
    from src.orchestration.query_orchestrator import QueryOrchestrator

    validator = StubTokenValidator()
    retriever = StubRetrievalPort(chunks=[])
    generator = StubGenerationPort()

    orchestrator = QueryOrchestrator(
        token_validator=validator,
        retriever=retriever,
        generator=generator,
    )

    result = orchestrator.execute(
        query="Topic not in corpus",
        bearer_token="Bearer valid.token",
    )

    assert result.behavior == BehaviorEnum.ABSTAIN
    assert len(result.citations) == 0


def test_orchestrator_rejects_unauthenticated_requests() -> None:
    """Verify orchestrator raises AuthenticationError on invalid credentials."""
    from src.orchestration.query_orchestrator import QueryOrchestrator

    validator = StubTokenValidator(should_fail=True)
    retriever = StubRetrievalPort()
    generator = StubGenerationPort()

    orchestrator = QueryOrchestrator(
        token_validator=validator,
        retriever=retriever,
        generator=generator,
    )

    with pytest.raises(AuthenticationError, match="Invalid or missing token"):
        orchestrator.execute(query="Any query", bearer_token="")

