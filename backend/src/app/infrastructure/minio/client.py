"""MinIO adapter implementing the object-storage port.

The ``minio`` SDK is synchronous, so blocking calls are offloaded to a worker
thread to keep the async event loop free.
"""

import asyncio
import io
import logging

from minio import Minio
from minio.error import S3Error

from app.domain.interfaces.object_storage import IObjectStorage
from app.infrastructure.minio.exceptions import ObjectStorageError

logger = logging.getLogger(__name__)


class MinioObjectStorage(IObjectStorage):
    """Stores document bytes in a single MinIO bucket."""

    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        try:
            await asyncio.to_thread(self._put_object, key, data, content_type)
        except S3Error as exc:
            raise ObjectStorageError(f"failed to store object {key!r}") from exc

    def _put_object(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    async def get(self, key: str) -> bytes:
        try:
            return await asyncio.to_thread(self._get_object, key)
        except S3Error as exc:
            raise ObjectStorageError(f"failed to fetch object {key!r}") from exc

    def _get_object(self, key: str) -> bytes:
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def ensure_bucket(self) -> None:
        """Create the target bucket if it does not already exist (blocking)."""
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
            logger.info("created object storage bucket %s", self._bucket)
