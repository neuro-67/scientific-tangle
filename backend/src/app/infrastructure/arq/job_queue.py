"""arq adapter implementing the job-queue port."""

import logging
from uuid import UUID

from arq import ArqRedis

from app.domain.interfaces.job_queue import IJobQueue
from app.infrastructure.arq.constants import PROCESS_DOCUMENT_JOB

logger = logging.getLogger(__name__)


class ArqJobQueue(IJobQueue):
    """Enqueues jobs onto an arq/Redis-backed worker."""

    def __init__(self, pool: ArqRedis) -> None:
        self._pool = pool

    async def enqueue_document_processing(self, document_id: UUID) -> None:
        await self._pool.enqueue_job(PROCESS_DOCUMENT_JOB, str(document_id))
        logger.info("enqueued document processing", extra={"document_id": str(document_id)})
