"""``answers`` table — persisted history of /query/ask responses."""

from sqlalchemy import Column, DateTime, JSON, String, Table, Text, Uuid

from app.infrastructure.database.base import Base

answers_table = Table(
    "answers",
    Base.metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("question", Text, nullable=False),
    Column("query_spec", JSON, nullable=False),
    Column("synthesis", JSON, nullable=False),
    Column("subgraph", JSON, nullable=False),
    Column("confidence", String(32), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, index=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
