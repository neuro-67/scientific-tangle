"""DTOs for answer-history read + regenerate endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnswerRecord(BaseModel):
    """A saved /query/ask response with the full envelope needed to re-render."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question: str
    query_spec: dict[str, Any]
    synthesis: dict[str, Any]
    subgraph: dict[str, Any]
    confidence: str | None
    created_at: datetime
    updated_at: datetime


class AnswerListItem(BaseModel):
    """Lightweight row for the history list — omits the heavy jsonb columns."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question: str
    confidence: str | None
    created_at: datetime
    updated_at: datetime
