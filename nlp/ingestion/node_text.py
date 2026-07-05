"""Build the searchable text for a graph node.

Vector search embeds one string per node. Early ingestion embedded only
``id — description``, but ~90% of nodes have no ``description`` at all, so the
embedded text collapsed to a bare entity name (median 22 chars). That still
retrieves the right entity, but leaves synthesis with nothing to elaborate on
("finds the node, says nothing").

Most nodes *do* carry meaningful structured attributes the LLM extracted —
a Process has ``domain``/``method``/``technique``, a Property has
``unit``/``value``/``formula``, a Measurement has ``value``/``unit``/``min``/
``max``, a Finding has ``statement``/``equation``. Folding those into the text
gives both a stronger embedding and real content for the synthesis prompt.

This is shared by the live re-embed and the ingest-time Qdrant upload so both
paths produce identical, richer text.
"""

from __future__ import annotations

from typing import Any

# Bookkeeping / provenance fields — never part of the semantic text.
_METADATA_KEYS = frozenset(
    {
        "id",
        "ingestion_date",
        "validation_status",
        "confidence",
        "source_document",
        "doc_id",
        "geography",
        "line",
        "verified",
        "stub",
        "version",
        "archived",
        "superseded_by",
        "valid_from",
        "valid_to",
        "revision_of",
        "embedding",
        "operator",  # only meaningful glued to value/unit (handled below)
        "unit_normalized_from",
    }
)

# Attribute keys rendered as a leading "value unit" measurement phrase.
_NUMERIC_KEYS = ("value", "unit", "min", "max")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(_clean(v) for v in value if _clean(v))
    return str(value).strip()


def build_node_text(node_id: str, label: str, props: dict[str, Any] | None) -> str:
    """Return a compact, content-rich string to embed for one node."""
    props = props or {}
    node_id = (node_id or "").strip()

    parts: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        text = text.strip(" ;,—-")
        low = text.lower()
        if text and low not in seen and low != node_id.lower():
            seen.add(low)
            parts.append(text)

    # Measurement-style numeric payload: "= 237 мм", "0.05–0.12 моль/л".
    op = _clean(props.get("operator"))
    val = _clean(props.get("value"))
    unit = _clean(props.get("unit"))
    vmin = _clean(props.get("min"))
    vmax = _clean(props.get("max"))
    if val:
        add(" ".join(x for x in (op, val, unit) if x))
    elif vmin or vmax:
        rng = "–".join(x for x in (vmin, vmax) if x)
        add(" ".join(x for x in (rng, unit) if x))

    # Everything else that isn't metadata or already-consumed numeric fields.
    for key, raw in props.items():
        if key in _METADATA_KEYS or key in _NUMERIC_KEYS:
            continue
        add(_clean(raw))

    if not parts:
        return node_id
    return f"{node_id} — " + "; ".join(parts)
