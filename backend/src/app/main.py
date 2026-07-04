"""FastAPI application entrypoint. Consumes only the composition registry."""

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from app.features.registry.providers import PROVIDERS
from app.features.registry.routers import ROUTERS
from app.infrastructure.logging import configure_logging


def create_app() -> FastAPI:
    """Build the FastAPI application from the composition registry."""
    configure_logging()

    app = FastAPI(
        title="Scientific Tangle API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    for router in ROUTERS:
        app.include_router(router)

    container = make_async_container(*PROVIDERS)
    setup_dishka(container=container, app=app)
    return app


app = create_app()
