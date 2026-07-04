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
    # arq's default (300s) is too short for process_document: a single
    # ingestion already takes ~5min in isolation, and it gets much slower
    # once several documents run concurrently and compete for the same LLM
    # calls -- confirmed on a real 20-document batch, where several jobs hit
    # the default timeout mid-run. asyncio.wait_for's resulting
    # CancelledError also isn't an Exception subclass, so it skipped the
    # handler's except block entirely and left documents stuck in
    # PROCESSING forever with no failure ever recorded.
    job_timeout = 3600
    # arq's default is 10 concurrent jobs, but every job hammers the same
    # RouterAI endpoint -- at 10-way concurrency the shared LLM throughput
    # collapses (180s read timeouts) and big documents (400+ chunks) blow the
    # job_timeout. Fewer concurrent documents each get more LLM throughput and
    # finish before timing out. Confirmed on the 104-doc Обзоры batch.
    max_jobs = 3
