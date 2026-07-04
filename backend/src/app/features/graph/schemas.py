"""DTOs for graph CRUD endpoints (Neo4j write layer)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GraphNodeCreate(BaseModel):
    """Payload for creating a new node."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1, max_length=64, description="Neo4j label")
    label: str = Field(min_length=1, max_length=512, description="Display label / name")
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphNodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=512)
    properties: dict[str, Any] | None = None


class GraphEdgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, description="source node id (matches n.id)")
    target: str = Field(min_length=1)
    type: str = Field(
        min_length=1,
        max_length=64,
        description="Relationship type (uppercase snake_case recommended)",
    )
    label: str | None = Field(default=None, max_length=512)


class GraphEdgeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=512)


class GraphNodeResponse(BaseModel):
    id: str
    label: str
    type: str


class GraphEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    type: str
    label: str | None = None


class FactRevisionResponse(BaseModel):
    superseded_at: str
    superseded_by_document: str | None = None
    previous_properties: dict[str, Any]
