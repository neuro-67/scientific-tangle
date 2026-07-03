"""Background task wiring — the only place that lists every arq task function."""

from collections.abc import Callable

from app.features.document.process.task import process_document

TASKS: list[Callable[..., object]] = [
    process_document,
]
