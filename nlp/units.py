"""Unit normalization (docs/NLP_PIPELINE.md [5] Normalize: "мг/дм³ → мг/л").

pint's registry only parses Latin unit symbols, but the LLM extracts
Cyrillic ones (мг, л, дм³, ...) -- this module translates between them and
does the actual conversion math with pint rather than a hand-rolled table,
so compound units (мг/л, г/дм³, ...) and non-1:1 conversions (г/л -> мг/л
needs *1000) are handled correctly, not just aliased.

Scope: concentration units (mass/volume), since that's the one conversion
the ontology docs give as a concrete example and the dominant unit family
in this domain (сульфаты/хлориды/... в мг/л). Unrecognized units (length,
pressure, temperature, or free-text like "раз", "линия") pass through
unchanged rather than raising -- this is a best-effort normalizer, not a
strict validator.
"""

from __future__ import annotations

import pint

_ureg = pint.UnitRegistry()

# Cyrillic unit string (lowercased) -> pint-parseable expression.
# дм³ (cubic decimeter) is exactly a liter by definition (1 дм³ = 1 л) --
# this is where "мг/дм³ → мг/л" comes from: it's a relabeling, not a scaling.
_UNIT_ALIASES: dict[str, str] = {
    "мг": "milligram",
    "г": "gram",
    "кг": "kilogram",
    "мкг": "microgram",
    "л": "liter",
    "дм3": "liter",
    "дм³": "liter",
    "мл": "milliliter",
    "м3": "meter ** 3",
    "м³": "meter ** 3",
}

CANONICAL_CONCENTRATION_UNIT = "мг/л"


def _parse_compound_unit(unit: str) -> str | None:
    """Translate a Cyrillic compound unit string (e.g. "мг/дм³") into a
    pint-parseable expression (e.g. "milligram / liter")."""
    unit = unit.strip().lower().replace(" ", "")
    if "/" in unit:
        num, _, den = unit.partition("/")
        num_p = _UNIT_ALIASES.get(num)
        den_p = _UNIT_ALIASES.get(den)
        if num_p and den_p:
            return f"{num_p} / {den_p}"
        return None
    return _UNIT_ALIASES.get(unit)


def is_concentration_unit(unit: str) -> bool:
    return _parse_compound_unit(unit) is not None


def convert(value: float, unit: str, target_unit: str = CANONICAL_CONCENTRATION_UNIT) -> tuple[float, str] | None:
    """Convert `value` from `unit` to `target_unit`.

    Returns None if either unit isn't a recognized concentration unit
    (e.g. free-text units like "раз", "линия", or units outside this
    module's scope like °C/Па/мм) -- callers should leave those unchanged.
    """
    src = _parse_compound_unit(unit)
    tgt = _parse_compound_unit(target_unit)
    if not src or not tgt:
        return None
    try:
        quantity = _ureg.Quantity(value, src).to(tgt)
        return round(float(quantity.magnitude), 6), target_unit
    except Exception:
        return None


def normalize_measurement_units(nodes: list[dict]) -> list[dict]:
    """Normalize concentration units on Measurement nodes to a canonical
    form (мг/л), converting value/min/max together so a range stays a
    valid range after conversion."""
    for node in nodes:
        if node.get("label") != "Measurement":
            continue
        props = node.get("properties", {})
        unit = props.get("unit", "")
        if not unit or unit == CANONICAL_CONCENTRATION_UNIT:
            continue
        if not is_concentration_unit(unit):
            continue
        changed = False
        for key in ("value", "min", "max"):
            if isinstance(props.get(key), (int, float)):
                result = convert(props[key], unit)
                if result is not None:
                    props[key], _ = result
                    changed = True
        if changed:
            props["unit"] = CANONICAL_CONCENTRATION_UNIT
            props["unit_normalized_from"] = unit
    return nodes
