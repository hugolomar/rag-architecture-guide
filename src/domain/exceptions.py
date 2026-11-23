"""Domain and infrastructure error boundaries for the governed RAG system."""


class DomainError(Exception):
    """Base exception for all domain and governed execution errors."""


class AuthenticationError(DomainError):
    """Raised when bearer token is missing, forged, expired, or claims are invalid."""


class UpstreamProviderError(DomainError):
    """Base exception for external infrastructure failures (Qdrant, LLM providers, network)."""


class RetrievalProviderError(UpstreamProviderError):
    """Raised when hybrid vector search, embedding generation, or database access fails."""


class GenerationProviderError(UpstreamProviderError):
    """Raised when external generative LLM provider fails or becomes unreachable."""
