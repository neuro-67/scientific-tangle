"""DI provider for the get-document slice."""

from dishka import Provider, Scope, provide

from app.features.document.get.handler import GetDocumentHandler
from app.features.document.get.repository import GetDocumentRepository


class GetDocumentProvider(Provider):
    """Wires the get-document handler and repository."""

    scope = Scope.REQUEST
    repository = provide(GetDocumentRepository)
    handler = provide(GetDocumentHandler)
