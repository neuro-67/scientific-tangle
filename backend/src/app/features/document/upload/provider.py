"""DI provider for the upload-document slice."""

from dishka import Provider, Scope, provide

from app.features.document.upload.handler import UploadDocumentHandler
from app.features.document.upload.repository import UploadDocumentRepository


class UploadDocumentProvider(Provider):
    """Wires the upload-document handler and repository."""

    scope = Scope.REQUEST
    repository = provide(UploadDocumentRepository)
    handler = provide(UploadDocumentHandler)
