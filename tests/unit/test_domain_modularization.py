"""Unit tests for domain modularization and bounded context separation.

Verifies that domain entities are partitioned cleanly across documents.py and
queries.py, with public re-exports in __init__.py and backward compatibility via
models.py.
"""

from enum import StrEnum

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


# ==========================================
# RE-EXPORT FACADE & BACKWARD COMPATIBILITY
# ==========================================


def test_domain_facade_reexports_document_entities() -> None:
    """Verify that domain facade re-exports document lifecycle entities."""
    from src.domain import (
        CanonicalDocument,
        GovernedChunk,
        ManifestRecord,
        VectorizedChunk,
    )

    assert ManifestRecord is not None
    assert CanonicalDocument is not None
    assert GovernedChunk is not None
    assert VectorizedChunk is not None


def test_domain_models_module_backward_compatibility() -> None:
    """Verify that legacy models.py preserves aliases for backward compatibility."""
    from src.domain.models import (
        CanonicalDocument,
        GovernedChunk,
        ManifestRecord,
        VectorizedChunk,
    )

    assert ManifestRecord is not None
    assert CanonicalDocument is not None
    assert GovernedChunk is not None
    assert VectorizedChunk is not None


# ==========================================
# BEHAVIOR ENUM & QUERY ENTITIES
# ==========================================


def test_behavior_enum_values() -> None:
    """Verify BehaviorEnum contains exactly the four closed governed behaviors."""
    from src.domain.enums import BehaviorEnum

    assert issubclass(BehaviorEnum, StrEnum)
    expected = {"ground_answer", "deny_access", "abstain", "clarify"}
    actual = {b.value for b in BehaviorEnum}
    assert actual == expected


def test_citation_model_validation() -> None:
    """Verify Citation attributes and immutability."""
    from src.domain.queries import Citation

    citation = Citation(doc_id="DOC-ENG-001", chunk_id="DOC-ENG-001#c0")
    assert citation.doc_id == "DOC-ENG-001"
    assert citation.chunk_id == "DOC-ENG-001#c0"

    with pytest.raises(ValidationError, match="extra"):
        Citation.model_validate({"doc_id": "DOC-ENG-001", "chunk_id": "c0", "extra_field": "bad"})


def test_caller_context_validation() -> None:
    """Verify CallerContext attributes and group membership."""
    from src.domain.queries import CallerContext

    ctx = CallerContext(user_id="user-123", groups={"engineering-core", "all-employees"})
    assert ctx.user_id == "user-123"
    assert "engineering-core" in ctx.groups

    with pytest.raises(ValidationError, match="extra"):
        CallerContext.model_validate({"user_id": "u1", "groups": ["g1"], "forged": True})


def test_retrieved_chunk_validation() -> None:
    """Verify RetrievedChunk attributes and score bounds."""
    from src.domain.queries import RetrievedChunk

    chunk = RetrievedChunk(
        chunk_id="DOC-ENG-001#c0",
        doc_id="DOC-ENG-001",
        text="Sample policy excerpt.",
        score=0.88,
        allowed_groups=["engineering-core"],
    )
    assert chunk.score == 0.88
    assert chunk.doc_id == "DOC-ENG-001"

    with pytest.raises(ValidationError, match="extra"):
        RetrievedChunk.model_validate(
            {
                "chunk_id": "c0",
                "doc_id": "DOC-001",
                "text": "t",
                "score": 0.5,
                "allowed_groups": [],
                "extra": 1,
            }
        )


def test_generation_result_validation() -> None:
    """Verify GenerationResult captures answer, behavior, and citations."""
    from src.domain.enums import BehaviorEnum
    from src.domain.queries import Citation, GenerationResult

    res = GenerationResult(
        answer="Grounded response text.",
        behavior=BehaviorEnum.GROUND_ANSWER,
        citations=[Citation(doc_id="DOC-ENG-001", chunk_id="DOC-ENG-001#c0")],
    )
    assert res.behavior == BehaviorEnum.GROUND_ANSWER
    assert len(res.citations) == 1


# ==========================================
# ABSTRACT DOMAIN PORTS
# ==========================================


def test_abstract_domain_ports_instantiation_prohibited() -> None:
    """Verify that abstract ports fail loud if instantiated directly."""
    from src.domain.ports.generation import GenerationPort
    from src.domain.ports.identity import TokenValidatorPort
    from src.domain.ports.retrieval import RetrievalPort

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        TokenValidatorPort()  # type: ignore[abstract]

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        RetrievalPort()  # type: ignore[abstract]

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        GenerationPort()  # type: ignore[abstract]
