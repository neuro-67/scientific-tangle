"""FastAPI application entrypoint. Consumes only the composition registry."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine

from app.features.registry.providers import PROVIDERS
from app.features.registry.routers import ROUTERS
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.bootstrap import create_all
from app.infrastructure.errors.handlers import register_exception_handlers
from app.infrastructure.logging import configure_logging


def create_app() -> FastAPI:
    """Build the FastAPI application from the composition registry."""
    configure_logging()
    container = make_async_container(*PROVIDERS)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        engine = await container.get(AsyncEngine)
        await create_all(engine)
        yield
        await container.close()

    app = FastAPI(
        title="Scientific Tangle API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in ROUTERS:
        app.include_router(router)

    register_exception_handlers(app)
    setup_dishka(container=container, app=app)
    return app


app = create_app()
