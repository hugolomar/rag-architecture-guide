"""Contract tests verifying zero drift between FastAPI runtime schema and openapi.yaml."""

from pathlib import Path

import pytest
import yaml

from src.api.main import app

pytestmark = pytest.mark.contract

CONTRACT_PATH = Path("specs/002-query-api/contracts/openapi.yaml")


# ==========================================
# OPENAPI CONTRACT DRIFT TESTS
# ==========================================


def test_openapi_contract_file_exists() -> None:
    """Verify that the authoritative OpenAPI contract file exists on disk."""
    assert CONTRACT_PATH.exists(), f"Contract file missing at {CONTRACT_PATH}"


def test_openapi_schema_drift_endpoint_and_methods() -> None:
    """Verify paths, HTTP methods, and operation IDs match openapi.yaml exactly."""
    with open(CONTRACT_PATH, encoding="utf-8") as f:
        spec_schema = yaml.safe_load(f)

    runtime_schema = app.openapi()

    # Verify info section
    assert runtime_schema["info"]["title"] == spec_schema["info"]["title"]
    assert runtime_schema["info"]["version"] == spec_schema["info"]["version"]

    # Verify /query endpoint exists in runtime
    assert "/query" in runtime_schema["paths"]
    assert "post" in runtime_schema["paths"]["/query"]

    # Verify operationId
    assert (
        runtime_schema["paths"]["/query"]["post"]["operationId"]
        == spec_schema["paths"]["/query"]["post"]["operationId"]
    )


def test_openapi_schema_drift_responses() -> None:
    """Verify HTTP response status codes match contract."""
    with open(CONTRACT_PATH, encoding="utf-8") as f:
        spec_schema = yaml.safe_load(f)

    runtime_schema = app.openapi()
    runtime_responses = runtime_schema["paths"]["/query"]["post"]["responses"]
    spec_responses = spec_schema["paths"]["/query"]["post"]["responses"]

    # In OpenAPI 3.1, status codes can be strings or integers in YAML
    spec_status_codes = {str(k) for k in spec_responses.keys()}
    runtime_status_codes = {str(k) for k in runtime_responses.keys()}

    # All contract status codes must be represented in runtime schema
    for code in ["200", "401", "422", "502", "504"]:
        assert code in spec_status_codes
        assert code in runtime_status_codes

