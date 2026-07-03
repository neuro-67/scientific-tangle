"""Generic base repository backed by an AsyncSession."""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Slice repositories subclass this and add use-case queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
