"""OIDC JWT bearer token validator adapter.

Implements TokenValidatorPort by verifying cryptographic signatures (RS256),
issuer, audience, and expiration constraints using PyJWT and cryptography,
extracting authoritative caller identity and group claims.
"""

from typing import Any

import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    PyJWTError,
)

from src.domain.ports.identity import TokenValidatorPort
from src.domain.queries import CallerContext


class AuthenticationError(Exception):
    """Raised when bearer token verification or claim extraction fails."""


class OIDCValidatorAdapter(TokenValidatorPort):
    """Verifies OIDC bearer tokens against authoritative public keys."""

    def __init__(
        self,
        public_key: str,
        expected_issuer: str,
        expected_audience: str,
        algorithm: str = "RS256",
    ) -> None:
        """Initialize the OIDC validator.

        Args:
            public_key: RSA public key in PEM format or JWKS public key string.
            expected_issuer: Authoritative OIDC issuer URL.
            expected_audience: Expected client audience identifier.
            algorithm: Cryptographic algorithm (defaults to RS256).
        """
        self.public_key = public_key
        self.expected_issuer = expected_issuer
        self.expected_audience = expected_audience
        self.algorithm = algorithm

    def validate_token(self, token: str) -> CallerContext:
        """Validate bearer token signature, claims, and expiry, returning verified caller context.

        Args:
            token: Encoded JWT bearer token string.

        Returns:
            CallerContext containing verified user_id and groups set.

        Raises:
            AuthenticationError: When token is missing, expired, forged, or invalid.
        """
        if not token or not token.strip():
            raise AuthenticationError("Missing authorization token")

        clean_token = token.strip()
        if clean_token.lower().startswith("bearer "):
            clean_token = clean_token[7:].strip()

        try:
            payload: dict[str, Any] = jwt.decode(
                clean_token,
                self.public_key,
                algorithms=[self.algorithm],
                issuer=self.expected_issuer,
                audience=self.expected_audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except ExpiredSignatureError as exc:
            raise AuthenticationError(f"Token has expired: {exc}") from exc
        except InvalidIssuerError as exc:
            raise AuthenticationError(f"Invalid issuer: {exc}") from exc
        except InvalidAudienceError as exc:
            raise AuthenticationError(f"Invalid audience: {exc}") from exc
        except PyJWTError as exc:
            raise AuthenticationError(f"Invalid token signature or structure: {exc}") from exc

        sub = payload.get("sub")
        if not sub or not isinstance(sub, str):
            raise AuthenticationError("Missing subject (sub) claim in token")

        raw_groups = payload.get("groups")
        if raw_groups is None or not isinstance(raw_groups, list):
            raise AuthenticationError("Missing groups claim in token")

        groups = {str(g) for g in raw_groups if isinstance(g, str)}

        return CallerContext(
            user_id=sub,
            groups=groups,
        )
