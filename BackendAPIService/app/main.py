from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.routers import admin, auth, kyc, users

logger = get_logger(__name__)

openapi_tags = [
    {"name": "Auth", "description": "Registration, login, and current-session endpoints."},
    {"name": "Users", "description": "End-user account APIs (self-service)."},
    {"name": "KYC", "description": "End-user KYC workflow: create/update submission, upload documents, status tracking."},
    {"name": "Admin", "description": "Administrator review workflow, filtering/search, user management, audit access."},
    {"name": "System", "description": "Service health and documentation helpers."},
]


def create_app() -> FastAPI:
    """Create and configure the FastAPI app instance."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="EKYC Backend API Service",
        description=(
            "FastAPI-based backend for EKYC workflows. Owns auth/roles, KYC orchestration, "
            "audit logging, and database persistence."
        ),
        version="0.1.0",
        openapi_tags=openapi_tags,
        docs_url="/docs" if settings.enable_openapi else None,
        redoc_url="/redoc" if settings.enable_openapi else None,
        openapi_url="/openapi.json" if settings.enable_openapi else None,
    )

    # CORS: allow frontend origin(s)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin] if settings.frontend_origin else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(kyc.router)
    app.include_router(admin.router)

    @app.get(
        "/health",
        tags=["System"],
        summary="Health check",
        description="Returns service health status for load balancers and monitoring.",
        operation_id="health_check",
    )
    # PUBLIC_INTERFACE
    def health_check() -> dict:
        """Health check endpoint.

        Returns:
            A small JSON payload indicating service health.
        """
        return {"status": "ok"}

    @app.get(
        "/docs/websocket-usage",
        tags=["System"],
        summary="WebSocket usage note (not implemented)",
        description=(
            "This project currently implements REST APIs only. If real-time notifications are later added "
            "via WebSockets, this endpoint should be updated with connection URLs and usage examples."
        ),
        operation_id="websocket_usage_note",
    )
    # PUBLIC_INTERFACE
    def websocket_usage_note() -> dict:
        """Explain current real-time capabilities (or lack thereof).

        Returns:
            A JSON payload explaining WebSocket support status.
        """
        return {
            "websocket_supported": False,
            "note": "Real-time notifications are not implemented yet; use REST polling for status.",
        }

    logger.info("BackendAPIService started", extra={"environment": settings.environment})
    return app


app = create_app()
