"""Import every ORM table here so metadata sees them."""

from app.infrastructure.database.tables.documents import documents_table
from app.infrastructure.database.tables.user import UserRow

__all__ = ["UserRow", "documents_table"]
