"""``documents`` table definition."""

from sqlalchemy import Column, DateTime, Enum, Integer, String, Table, Text, Uuid

from app.domain.entities.document import DocumentStatus
from app.infrastructure.database.base import Base

documents_table = Table(
    "documents",
    Base.metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("filename", String(1024), nullable=False),
    Column("content_type", String(255), nullable=False),
    Column("size", Integer, nullable=False),
    Column("storage_key", String(2048), nullable=False),
    Column(
        "status",
        Enum(DocumentStatus, native_enum=False, length=32, name="document_status"),
        nullable=False,
        index=True,
    ),
    Column("error", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
