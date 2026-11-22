"""Deterministic in-memory mock generation adapter for offline tests and evaluation."""

from src.domain.enums import BehaviorEnum
from src.domain.ports.generation import GenerationPort
from src.domain.queries import Citation, GenerationResult, RetrievedChunk


class MockGenerationAdapter(GenerationPort):
    """Deterministic generation adapter for hermetic testing without model calls."""

    def generate(
        self,
        query: str,
        context: list[RetrievedChunk],
        user_id: str,
    ) -> GenerationResult:
        """Synthesize answer text from context chunks without network access.

        Args:
            query: Natural language user query.
            context: List of retrieved evidence chunks.
            user_id: Caller identifier.

        Returns:
            GenerationResult containing synthesized answer and citations.
        """
        if not context:
            return GenerationResult(
                answer="I do not have enough information to answer this inquiry based on verified corporate documentation.",
                behavior=BehaviorEnum.ABSTAIN,
                citations=[],
            )

        # Synthesize deterministic answer text from provided chunk excerpts
        excerpts = [chunk.text for chunk in context]
        answer_text = f"Based on authorized documentation: {' '.join(excerpts)}"

        citations = [Citation(doc_id=chunk.doc_id, chunk_id=chunk.chunk_id) for chunk in context]

        return GenerationResult(
            answer=answer_text,
            behavior=BehaviorEnum.GROUND_ANSWER,
            citations=citations,
        )
