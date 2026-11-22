"""FastAPI application factory, lifespan management, and global middlewares."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.adapters.telemetry.otel_emitter import TelemetryManager
from src.api.config import APISettings
from src.api.routes import health, query


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage application startup and graceful shutdown with telemetry flush."""
    settings = APISettings()
    telemetry_manager = TelemetryManager(
        service_name=settings.service_name,
    )
    try:
        yield
    finally:
        # Guaranteed flush during server shutdown or unhandled runtime faults
        telemetry_manager.flush_and_shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Governed Query API and RAG Runtime",
        description="Contract-First HTTP specification for enterprise governed knowledge retrieval and grounded generation.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Attach routers
    app.include_router(health.router)
    app.include_router(query.router)

    # Custom exception handler for 422 validation errors matching OpenAPI schema
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exc.errors()},
        )

    return app


app = create_app()
