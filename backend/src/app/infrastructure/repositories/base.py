"""Generic base repositories backed by an ``AsyncSession``.

Two shapes coexist: ``BaseRepository`` for slices that write their own queries
against ORM rows, and ``SQLAlchemyRepository[T]`` for slices that persist a
mapped domain entity directly via CRUD primitives.
"""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository:
    """Slice repositories subclass this and add use-case queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session


class SQLAlchemyRepository(Generic[T]):
    """CRUD primitives over a mapped entity type ``T``."""

    model_type: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: T) -> None:
        """Persist a new entity, flushing so DB-assigned values are available."""
        self._session.add(entity)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> T | None:
        """Load an entity by primary key, or ``None`` if it does not exist."""
        return await self._session.get(self.model_type, entity_id)
