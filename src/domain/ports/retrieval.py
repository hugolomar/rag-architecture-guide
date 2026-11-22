"""Abstract port for security-trimmed hybrid retrieval."""

import abc

from src.domain.queries import RetrievedChunk


class RetrievalPort(abc.ABC):
    """Abstract behavioral port for security-trimmed hybrid vector retrieval."""

    @abc.abstractmethod
    def retrieve(
        self,
        query: str,
        caller_groups: set[str],
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        """Retrieve authorized candidate chunks using dense + sparse hybrid search.

        Must enforce pre-inference security trimming (allowed_groups and status != archived).

        Args:
            query: Natural language query string.
            caller_groups: Set of verified caller group claims.
            top_k: Maximum number of candidate chunks to return.

        Returns:
            List of authorized RetrievedChunk objects ordered by fused relevance score.
        """
        raise NotImplementedError
