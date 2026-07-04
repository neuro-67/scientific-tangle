"""Provenance endpoint: the full trust chain behind one fact.

Surfaces the provenance the graph already carries (confidence, Source spans,
mechanical number-verification, publication, authors, validators) so the UI
can answer "почему система в это верит" -- case-specification.md's verification
model. Read slice: injects the Neo4j driver and projects the analytics query
straight to JSON, no domain entities.
"""

from typing import Any

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, status
from neo4j import AsyncDriver

from nlp.query.retrieval.analytics import provenance_path

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get(
    "/provenance/{fact_id}",
    status_code=status.HTTP_200_OK,
    summary="Trust chain behind a fact",
    description="Confidence, source page spans, whether each measurement was "
    "verified against the raw document text, publication, authors and validators.",
)
@inject
async def get_provenance(
    fact_id: str,
    driver: FromDishka[AsyncDriver],
) -> dict[str, Any]:
    """Return the provenance / trust chain for a single fact node."""
    return await provenance_path(driver, fact_id)
