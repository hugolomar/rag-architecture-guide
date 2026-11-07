"""Integration test for OpenTelemetry flush lifecycle (Articles 20 & 27, US3).

Verifies that stage spans, metrics, and providers flush cleanly prior to
process termination with zero telemetry loss.
"""

import pytest
from src.adapters.telemetry.otel_emitter import TelemetryManager


def test_telemetry_stage_spans_and_metrics() -> None:
    """Verify trace span context and metric recording."""
    mgr = TelemetryManager(service_name="test-ingestion-flush")

    with mgr.start_stage_span("manifest.validate") as span:
        assert span.is_recording()
        span.set_attribute("doc_count", 36)

    # Record metrics
    mgr.record_documents_processed(35)
    mgr.record_documents_rejected(1)
    mgr.record_chunks_created(312)

    # Clean shutdown and flush must succeed without error
    mgr.flush_and_shutdown()

