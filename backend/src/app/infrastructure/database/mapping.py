"""Imperative mapping of domain entities onto ORM tables.

Domain entities stay persistence-ignorant; the binding lives here so that
``domain/`` never imports SQLAlchemy. ``run_mappers`` is invoked once at
startup (API and worker) before any query executes. It shares the declarative
``Base`` registry so entities and declarative rows live on one metadata.
"""

from app.domain.entities.document import Document
from app.infrastructure.database.base import Base
from app.infrastructure.database.tables.documents import documents_table

_mapped = False


def run_mappers() -> None:
    """Bind domain entities to their tables. Idempotent within a process."""
    global _mapped
    if _mapped:
        return
    Base.registry.map_imperatively(Document, documents_table)
    _mapped = True
