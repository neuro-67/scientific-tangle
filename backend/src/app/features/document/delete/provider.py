"""DI provider for the delete-document slice."""

from dishka import Provider, Scope, provide
from neo4j import AsyncDriver
from qdrant_client import QdrantClient

from app.features.document.delete.handler import DeleteDocumentHandler
from app.features.document.delete.repository import (
    DeleteDocumentRepository,
    Neo4jDocumentPurger,
    QdrantDocumentPurger,
)


class DeleteDocumentProvider(Provider):
    """Wires the delete-document handler and its cross-store purgers."""

    scope = Scope.REQUEST
    repository = provide(DeleteDocumentRepository)
    handler = provide(DeleteDocumentHandler)

    @provide(scope=Scope.REQUEST)
    def graph_purger(self, driver: AsyncDriver) -> Neo4jDocumentPurger:
        return Neo4jDocumentPurger(driver)

    @provide(scope=Scope.REQUEST)
    def vector_purger(self, client: QdrantClient) -> QdrantDocumentPurger:
        return QdrantDocumentPurger(client)
