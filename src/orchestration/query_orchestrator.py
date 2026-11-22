"""Domain orchestrator coordinating authentication, retrieval, and generation.

Implements the central query application service that executes:
1. Token validation and caller context resolution (TokenValidatorPort).
2. Security-trimmed hybrid vector retrieval (RetrievalPort).
3. Evidence-grounded generation and behavior resolution (GenerationPort).
"""

from src.domain.enums import BehaviorEnum
from src.domain.ports.generation import GenerationPort
from src.domain.ports.identity import TokenValidatorPort
from src.domain.ports.retrieval import RetrievalPort
from src.domain.queries import GenerationResult


class QueryOrchestrator:
    """Coordinates authentication, retrieval, and generation for user queries."""

    def __init__(
        self,
        token_validator: TokenValidatorPort,
        retriever: RetrievalPort,
        generator: GenerationPort,
    ) -> None:
        """Initialize the orchestrator with abstract domain ports.

        Args:
            token_validator: Behavioral port for JWT token validation.
            retriever: Behavioral port for security-trimmed hybrid retrieval.
            generator: Behavioral port for grounded generative synthesis.
        """
        self.token_validator = token_validator
        self.retriever = retriever
        self.generator = generator

    def execute(
        self,
        query: str,
        bearer_token: str,
        top_k: int = 3,
    ) -> GenerationResult:
        """Execute the governed query pipeline end-to-end.

        Args:
            query: Natural language inquiry.
            bearer_token: Encoded authorization bearer token.
            top_k: Maximum candidate chunks to retrieve.

        Returns:
            GenerationResult containing answer text, governed behavior, and citations.

        Raises:
            AuthenticationError: When bearer token validation fails.
        """
        # 1. Authoritative Identity Resolution
        caller_context = self.token_validator.validate_token(bearer_token)

        # 2. Security-Trimmed Hybrid Retrieval
        evidence = self.retriever.retrieve(
            query=query,
            caller_groups=caller_context.groups,
            top_k=top_k,
        )

        # 3. Handle Empty Retrieval
        if not evidence:
            return GenerationResult(
                answer="No relevant or authorized information was found to answer this inquiry.",
                behavior=BehaviorEnum.ABSTAIN,
                citations=[],
            )

        # 4. Evidence-Grounded Generative Answering
        generation_result = self.generator.generate(
            query=query,
            context=evidence,
            user_id=caller_context.user_id,
        )

        return generation_result
