"""DI provider for MinIO-backed object storage."""

from dishka import Provider, Scope, provide
from minio import Minio

from app.domain.interfaces.object_storage import IObjectStorage
from app.infrastructure.config.settings import AppSettings
from app.infrastructure.minio.client import MinioObjectStorage


class ObjectStorageProvider(Provider):
    """Wires the MinIO client and the object-storage port."""

    @provide(scope=Scope.APP)
    def minio_client(self, settings: AppSettings) -> Minio:
        minio = settings.minio
        return Minio(
            minio.endpoint,
            access_key=minio.root_user,
            secret_key=minio.root_password,
            secure=minio.secure,
        )

    @provide(scope=Scope.REQUEST)
    def object_storage(self, client: Minio, settings: AppSettings) -> IObjectStorage:
        return MinioObjectStorage(client, settings.minio.documents_bucket)
