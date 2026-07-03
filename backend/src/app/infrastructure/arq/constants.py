"""Shared arq wiring constants.

The job name is the single contract between the enqueuer (API side) and the
worker's registered task function — both MUST use this identifier.
"""

from arq.connections import RedisSettings

from app.infrastructure.config.settings import RedisSettings as AppRedisSettings

PROCESS_DOCUMENT_JOB = "process_document"


def build_redis_settings(settings: AppRedisSettings) -> RedisSettings:
    """Translate app config into arq's Redis connection settings."""
    return RedisSettings(
        host=settings.host,
        port=settings.port,
        database=settings.database,
    )
