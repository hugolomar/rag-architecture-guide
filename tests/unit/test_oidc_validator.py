"""Unit tests for OIDC token validator adapter.

Verifies cryptographic JWT verification, issuer/audience validation, expiration
checks, and caller context extraction from token claims.
"""

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.domain.ports.identity import TokenValidatorPort

pytestmark = pytest.mark.unit


# ==========================================
# RSA KEY FIXTURES & HELPER FUNCTIONS
# ==========================================


@pytest.fixture(scope="module")
def rsa_key_pair() -> tuple[str, str]:
    """Generate an RSA public/private key pair for JWT signing in PEM format."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    return private_pem, public_pem


def _build_test_token(
    private_key_pem: str,
    sub: str = "7f3a1c2e-8b44-4d1a-9e06-2c5b8a1d4f70",
    groups: list[str] | None = None,
    iss: str = "https://idp.crateexpectations.example/realms/enterprise",
    aud: str = "rag-query-api",
    exp_offset: int = 3600,
) -> str:
    """Create a signed JWT token for testing."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "iss": iss,
        "aud": aud,
        "iat": now,
        "exp": now + exp_offset,
        "groups": groups or ["all-employees", "engineering-core"],
    }
    return jwt.encode(payload, private_key_pem, algorithm="RS256")


# ==========================================
# HAPPY PATH & CLAIM EXTRACTION
# ==========================================


def test_validator_inherits_from_port(rsa_key_pair: tuple[str, str]) -> None:
    """Verify that OIDCValidatorAdapter satisfies TokenValidatorPort."""
    from src.adapters.auth.oidc_validator import OIDCValidatorAdapter

    _, public_pem = rsa_key_pair
    adapter = OIDCValidatorAdapter(
        public_key=public_pem,
        expected_issuer="https://idp.crateexpectations.example/realms/enterprise",
        expected_audience="rag-query-api",
    )
    assert isinstance(adapter, TokenValidatorPort)


def test_valid_token_extraction(rsa_key_pair: tuple[str, str]) -> None:
    """Verify successful validation and caller context extraction."""
    from src.adapters.auth.oidc_validator import OIDCValidatorAdapter

    private_pem, public_pem = rsa_key_pair
    token = _build_test_token(
        private_pem,
        sub="jordan-123",
        groups=["all-employees", "engineering-core"],
    )

    validator = OIDCValidatorAdapter(
        public_key=public_pem,
        expected_issuer="https://idp.crateexpectations.example/realms/enterprise",
        expected_audience="rag-query-api",
    )

    context = validator.validate_token(token)
    assert context.user_id == "jordan-123"
    assert context.groups == {"all-employees", "engineering-core"}


# ==========================================
# SECURITY REJECTIONS & EDGE CASES
# ==========================================


def test_expired_token_rejection(rsa_key_pair: tuple[str, str]) -> None:
    """Verify that expired tokens fail loud."""
    from src.adapters.auth.oidc_validator import AuthenticationError, OIDCValidatorAdapter

    private_pem, public_pem = rsa_key_pair
    token = _build_test_token(private_pem, exp_offset=-60)

    validator = OIDCValidatorAdapter(
        public_key=public_pem,
        expected_issuer="https://idp.crateexpectations.example/realms/enterprise",
        expected_audience="rag-query-api",
    )

    with pytest.raises(AuthenticationError, match="Token has expired"):
        validator.validate_token(token)


def test_invalid_issuer_rejection(rsa_key_pair: tuple[str, str]) -> None:
    """Verify that tokens from untrusted issuers fail loud."""
    from src.adapters.auth.oidc_validator import AuthenticationError, OIDCValidatorAdapter

    private_pem, public_pem = rsa_key_pair
    token = _build_test_token(private_pem, iss="https://rogue-idp.example")

    validator = OIDCValidatorAdapter(
        public_key=public_pem,
        expected_issuer="https://idp.crateexpectations.example/realms/enterprise",
        expected_audience="rag-query-api",
    )

    with pytest.raises(AuthenticationError, match="Invalid issuer"):
        validator.validate_token(token)


def test_invalid_audience_rejection(rsa_key_pair: tuple[str, str]) -> None:
    """Verify that tokens for different audiences fail loud."""
    from src.adapters.auth.oidc_validator import AuthenticationError, OIDCValidatorAdapter

    private_pem, public_pem = rsa_key_pair
    token = _build_test_token(private_pem, aud="other-api")

    validator = OIDCValidatorAdapter(
        public_key=public_pem,
        expected_issuer="https://idp.crateexpectations.example/realms/enterprise",
        expected_audience="rag-query-api",
    )

    with pytest.raises(AuthenticationError, match="Invalid audience"):
        validator.validate_token(token)


def test_missing_groups_claim_rejection(rsa_key_pair: tuple[str, str]) -> None:
    """Verify that tokens missing mandatory groups claim fail loud."""
    from src.adapters.auth.oidc_validator import AuthenticationError, OIDCValidatorAdapter

    private_pem, public_pem = rsa_key_pair
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user-1",
            "iss": "https://idp.crateexpectations.example/realms/enterprise",
            "aud": "rag-query-api",
            "exp": now + 3600,
        },
        private_pem,
        algorithm="RS256",
    )

    validator = OIDCValidatorAdapter(
        public_key=public_pem,
        expected_issuer="https://idp.crateexpectations.example/realms/enterprise",
        expected_audience="rag-query-api",
    )

    with pytest.raises(AuthenticationError, match="Missing groups claim"):
        validator.validate_token(token)
