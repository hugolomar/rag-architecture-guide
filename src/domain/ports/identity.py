"""Abstract port for cryptographic bearer token validation and claim extraction."""

import abc

from src.domain.queries import CallerContext


class TokenValidatorPort(abc.ABC):
    """Abstract behavioral port for bearer token verification."""

    @abc.abstractmethod
    def validate_token(self, token: str) -> CallerContext:
        """Validate bearer token signature, claims, and expiry, returning verified caller context.

        Args:
            token: Encoded JWT bearer token string.

        Returns:
            CallerContext containing verified user_id and groups set.

        Raises:
            AuthenticationError: When token is missing, expired, forged, or invalid.
        """
        raise NotImplementedError
