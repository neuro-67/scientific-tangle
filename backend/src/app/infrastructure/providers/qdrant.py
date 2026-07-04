"""DI provider for Qdrant client and vector-search adapter."""

from dishka import Provider, Scope, provide
from qdrant_client import QdrantClient

from app.domain.interfaces.vector_search import IVectorSearch
from app.infrastructure.config.settings import AppSettings
from app.infrastructure.qdrant.client import QdrantVectorSearch


class QdrantProvider(Provider):
    """Wires the Qdrant sync client and the vector-search port."""

    @provide(scope=Scope.APP)
    def qdrant_client(self, settings: AppSettings) -> QdrantClient:
        return QdrantClient(
            host=settings.qdrant.host,
            port=settings.qdrant.http_port,
            check_compatibility=False,
        )

    @provide(scope=Scope.REQUEST)
    def vector_search(self, client: QdrantClient) -> IVectorSearch:
        return QdrantVectorSearch(client)
