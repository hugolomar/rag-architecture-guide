"""Unit tests for telemetry formatting and data hygiene (Articles 20 & 22, US3).

Verifies that structured logs produce JSON on stdout with run_id, stage,
and ensure confidential document text or credentials are not leaked.
"""

import json
import logging

from src.adapters.telemetry.otel_emitter import (
    JsonLogFormatter,
    TelemetryManager,
    mask_sensitive_data,
)


def test_json_log_formatter_produces_structured_json() -> None:
    """Verify JSON output format and standard correlation fields."""
    formatter = JsonLogFormatter(run_id="run-test-123")
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=20,
        msg="Validated manifest records",
        args=(),
        exc_info=None,
    )
    record.stage = "manifest"  # type: ignore[attr-defined]

    formatted_str = formatter.format(record)
    data = json.loads(formatted_str)

    assert data["run_id"] == "run-test-123"
    assert data["level"] == "INFO"
    assert data["stage"] == "manifest"
    assert data["message"] == "Validated manifest records"
    assert "timestamp" in data


def test_telemetry_hygiene_masks_sensitive_data() -> None:
    """Verify that credentials and tokens are scrubbed from telemetry signals (Article 22)."""
    raw_message = "Connecting with Bearer eyJhbGciOiJIUzI1Ni... and password secret123"
    sanitized = mask_sensitive_data(raw_message)

    assert "secret123" not in sanitized
    assert "Bearer [REDACTED]" in sanitized or "[REDACTED]" in sanitized


def test_telemetry_manager_generates_run_id() -> None:
    """Verify that TelemetryManager generates a unique run_id with 'run-' prefix."""
    mgr = TelemetryManager(service_name="rag-ingestion-test")
    assert mgr.run_id.startswith("run-")
    assert len(mgr.run_id) > 8

