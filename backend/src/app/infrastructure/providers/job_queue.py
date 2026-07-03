"""DI provider for the arq-backed job queue."""

from collections.abc import AsyncIterator

from arq import ArqRedis, create_pool
from dishka import Provider, Scope, provide

from app.domain.interfaces.job_queue import IJobQueue
from app.infrastructure.arq.constants import build_redis_settings
from app.infrastructure.arq.job_queue import ArqJobQueue
from app.infrastructure.config.settings import AppSettings


class JobQueueProvider(Provider):
    """Wires the arq Redis pool and the job-queue port."""

    @provide(scope=Scope.APP)
    async def pool(self, settings: AppSettings) -> AsyncIterator[ArqRedis]:
        pool = await create_pool(build_redis_settings(settings.redis))
        yield pool
        await pool.aclose()

    @provide(scope=Scope.REQUEST)
    def job_queue(self, pool: ArqRedis) -> IJobQueue:
        return ArqJobQueue(pool)
