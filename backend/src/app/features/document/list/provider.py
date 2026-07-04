"""DI provider for the list-documents slice."""

from dishka import Provider, Scope, provide

from app.features.document.list.handler import ListDocumentsHandler
from app.features.document.list.repository import ListDocumentsRepository


class ListDocumentsProvider(Provider):
    scope = Scope.REQUEST
    repository = provide(ListDocumentsRepository)
    handler = provide(ListDocumentsHandler)
