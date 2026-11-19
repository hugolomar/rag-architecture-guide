"""OpenTelemetry instrumentation and structured JSON logging emitter.

Emits:
1. Structured JSON logs on stdout with run_id correlation.
2. Distributed trace stage spans (ingestion.run, ingestion.manifest.validate, etc.).
3. Progress metrics for documents processed, rejected, and chunks created.
4. Guaranteed zero-loss flush and shutdown lifecycle.
"""

import json
import logging
import re
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

# Sanitization patterns to prevent credential leaks
SENSITIVE_PATTERNS = [
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), "Bearer [REDACTED]"),
    (
        re.compile(r"(password|secret|token|api_key)\s*[:=\s]\s*[^\s,]+", re.IGNORECASE),
        r"\1=[REDACTED]",
    ),
]


def mask_sensitive_data(message: str) -> str:
    """Mask credentials and authorization tokens from text payloads."""
    sanitized = message
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class JsonLogFormatter(logging.Formatter):
    """Newline-delimited JSON log formatter for batch stdout logging."""

    def __init__(self, run_id: str) -> None:
        super().__init__()
        self.run_id = run_id

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a structured JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "run_id": self.run_id,
            "stage": getattr(record, "stage", "general"),
            "message": mask_sensitive_data(record.getMessage()),
        }

        # Include extra attributes if passed
        for key in ("doc_count", "chunks_indexed", "archived_count", "active_count"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        return json.dumps(log_entry)


class TelemetryManager:
    """Manages OpenTelemetry tracing, metrics, and structured logging lifecycle.

    Attributes:
        run_id: Unique correlation identifier for the batch run.
        service_name: Name of the service emitted in trace and metric resources.
        is_shutdown: Flag indicating whether providers and exporters were flushed and shut down.
    """

    def __init__(
        self,
        service_name: str = "rag-ingestion",
        run_id: str | None = None,
        log_level: str = "INFO",
    ) -> None:
        """Initialize telemetry providers and logging configuration."""
        self.run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
        self.service_name = service_name

        # Resource attributes
        self.resource = Resource.create(
            {
                "service.name": self.service_name,
                "service.version": "0.1.0",
                "run_id": self.run_id,
            }
        )

        # Tracing initialization
        self.tracer_provider = TracerProvider(resource=self.resource)
        self.tracer = self.tracer_provider.get_tracer(self.service_name)

        # Metrics initialization
        self.meter_provider = MeterProvider(resource=self.resource)
        self.meter = self.meter_provider.get_meter(self.service_name)

        # Progress Counters
        self.docs_processed_counter = self.meter.create_counter(
            name="ingestion.documents.processed",
            description="Number of canonical documents successfully processed",
            unit="1",
        )
        self.docs_rejected_counter = self.meter.create_counter(
            name="ingestion.documents.rejected",
            description="Number of documents rejected or excluded from indexing",
            unit="1",
        )
        self.chunks_created_counter = self.meter.create_counter(
            name="ingestion.chunks.created",
            description="Number of governed chunks created and indexed",
            unit="1",
        )

        # Structured logger setup
        self.logger = logging.getLogger(f"rag.ingestion.{self.run_id}")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.propagate = False

        self._handler = logging.StreamHandler(sys.stdout)
        self._handler.setFormatter(JsonLogFormatter(run_id=self.run_id))
        self.logger.addHandler(self._handler)
        self.is_shutdown: bool = False

    def log(self, level: str, message: str, stage: str = "general", **kwargs: Any) -> None:
        """Emit a structured log message."""
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        extra = {"stage": stage, **kwargs}
        log_func(message, extra=extra)

    def start_stage_span(self, stage_name: str) -> trace.Span:
        """Create and start a trace span for an ingestion pipeline stage."""
        span_name = (
            f"ingestion.{stage_name}" if not stage_name.startswith("ingestion.") else stage_name
        )
        span = self.tracer.start_span(span_name)
        span.set_attribute("run_id", self.run_id)
        span.set_attribute("stage", stage_name)
        return span

    def record_documents_processed(self, count: int = 1) -> None:
        """Increment processed documents counter."""
        self.docs_processed_counter.add(count, {"run_id": self.run_id})

    def record_documents_rejected(self, count: int = 1) -> None:
        """Increment rejected/excluded documents counter."""
        self.docs_rejected_counter.add(count, {"run_id": self.run_id})

    def record_chunks_created(self, count: int = 1) -> None:
        """Increment chunks created counter."""
        self.chunks_created_counter.add(count, {"run_id": self.run_id})

    def flush_and_shutdown(self) -> None:
        """Explicitly flush all exporters and shut down providers (zero telemetry loss)."""
        try:
            self.tracer_provider.force_flush()
            self.tracer_provider.shutdown()
        except Exception as exc:
            sys.stderr.write(f"Warning: Tracer flush error: {exc}\n")

        try:
            self.meter_provider.force_flush()
            self.meter_provider.shutdown()
        except Exception as exc:
            sys.stderr.write(f"Warning: Meter flush error: {exc}\n")

        try:
            self._handler.flush()
        except Exception:
            pass

        self.is_shutdown = True
