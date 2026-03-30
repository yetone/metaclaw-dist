"""FastAPI application factory for MetaClaw web server."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from metaclaw import __version__
from metaclaw.config import MetaClawConfig


def create_app(config: MetaClawConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="MetaClaw",
        description="Skill-first LLM agent platform with multi-channel bridging",
        version=__version__,
    )

    # CORS
    if config:
        origins = config.web.cors_origins
    else:
        origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    from metaclaw.web.routes.health import router as health_router
    from metaclaw.web.routes.webhooks import router as webhook_router
    from metaclaw.web.routes.api import router as api_router

    app.include_router(health_router)
    app.include_router(webhook_router, prefix="/webhook")
    app.include_router(api_router, prefix="/api")

    return app
