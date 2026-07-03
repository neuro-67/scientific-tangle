"""Input DTO for the upload-document use case."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UploadDocumentCommand:
    """A document's bytes and metadata, ready to be stored and registered."""

    filename: str
    content_type: str
    content: bytes
