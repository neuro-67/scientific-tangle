"""arq worker entrypoint. Run with: ``arq app.worker.WorkerSettings``.

Builds a dishka container so background tasks resolve the same handlers and
unit-of-work boundary as the API. Each task opens a request scope (see
``features/document/process/task.py``).
"""

from typing import Any

from arq.connections import RedisSettings
from dishka import make_async_container
from sqlalchemy.ext.asyncio import AsyncEngine

from app.features.registry.providers import PROVIDERS
from app.features.registry.tasks import TASKS
from app.infrastructure.arq.constants import build_redis_settings
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.bootstrap import create_all
from app.infrastructure.database.mapping import run_mappers
from app.infrastructure.logging import configure_logging


async def startup(ctx: dict[str, Any]) -> None:
    """Wire logging, ORM mappings, schema and the DI container for the worker."""
    configure_logging()
    run_mappers()
    container = make_async_container(*PROVIDERS)
    engine = await container.get(AsyncEngine)
    await create_all(engine)
    ctx["container"] = container


async def shutdown(ctx: dict[str, Any]) -> None:
    """Tear down the DI container (closing the engine and Redis pool)."""
    await ctx["container"].close()


class WorkerSettings:
    """arq worker configuration consumed by the ``arq`` CLI."""

    functions = TASKS
    on_startup = startup
    on_shutdown = shutdown
    redis_settings: RedisSettings = build_redis_settings(get_settings().redis)
