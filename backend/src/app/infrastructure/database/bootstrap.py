"""Create tables from ORM metadata.

Pragmatic bootstrap for the hackathon in place of Alembic migrations —
safe to call repeatedly (CREATE TABLE IF NOT EXISTS semantics).
"""

from sqlalchemy.ext.asyncio import AsyncEngine

from app.infrastructure.database.base import Base
from app.infrastructure.database.tables import (  # noqa: F401  (register tables)
    UserRow as _UserRow,
    answers_table as _answers_table,
    documents_table as _documents_table,
)


async def create_all(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
