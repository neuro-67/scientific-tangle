"""Import every ORM table here so metadata sees them."""

from app.infrastructure.database.tables.answers import answers_table
from app.infrastructure.database.tables.documents import documents_table
from app.infrastructure.database.tables.user import UserRow

__all__ = ["UserRow", "answers_table", "documents_table"]
