"""Abstract port for evidence-grounded generative answering."""

import abc

from src.domain.queries import GenerationResult, RetrievedChunk


class GenerationPort(abc.ABC):
    """Abstract behavioral port for evidence-grounded generation."""

    @abc.abstractmethod
    def generate(
        self,
        query: str,
        context: list[RetrievedChunk],
        user_id: str,
    ) -> GenerationResult:
        """Synthesize answer strictly from retrieved context and classify behavior.

        Must isolate evidence within protective delimiters to prevent prompt injection.

        Args:
            query: Natural language inquiry.
            context: List of authorized evidence chunks retrieved for the query.
            user_id: Verified caller identifier for audit correlation.

        Returns:
            GenerationResult containing answer text, governed behavior, and citations.
        """
        raise NotImplementedError
