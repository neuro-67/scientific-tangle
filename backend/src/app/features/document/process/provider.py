"""DI provider for the process-document slice."""

from dishka import Provider, Scope, provide

from app.features.document.process.handler import ProcessDocumentHandler
from app.features.document.process.repository import ProcessDocumentRepository


class ProcessDocumentProvider(Provider):
    """Wires the process-document handler and repository."""

    scope = Scope.REQUEST
    repository = provide(ProcessDocumentRepository)
    handler = provide(ProcessDocumentHandler)
