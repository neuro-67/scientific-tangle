"""FastAPI application entrypoint. Consumes only the composition registry."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncEngine

from app.features.registry.providers import PROVIDERS
from app.features.registry.routers import ROUTERS
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.bootstrap import create_all
from app.infrastructure.database.mapping import run_mappers
from app.infrastructure.errors.handlers import register_exception_handlers
from app.infrastructure.logging import configure_logging
from app.infrastructure.minio.client import MinioObjectStorage


def create_app() -> FastAPI:
    """Build the FastAPI application from the composition registry."""
    configure_logging()
    run_mappers()

    container = make_async_container(*PROVIDERS)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        engine = await container.get(AsyncEngine)
        await create_all(engine)
        client = await container.get(Minio)
        bucket = get_settings().minio.documents_bucket
        await asyncio.to_thread(MinioObjectStorage(client, bucket).ensure_bucket)
        yield
        await container.close()

    # docs_url disabled — served manually below with a *relative* openapi_url
    # so Swagger UI works both locally (`/docs`) and behind a reverse-proxy
    # prefix (`/api/docs`) without any env config.
    app = FastAPI(
        title="Scientific Tangle API",
        version="0.1.0",
        docs_url=None,
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    @app.get("/docs", include_in_schema=False)
    def swagger_ui() -> object:
        # Relative URL: browser resolves against the current path, so
        # `/docs` → `/openapi.json`, `/api/docs` → `/api/openapi.json`.
        return get_swagger_ui_html(
            openapi_url="openapi.json",
            title=f"{app.title} — Swagger UI",
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
