"""After-commit callback queue for the unit of work.

Side effects that must run only once the transaction is durable — enqueuing a
background job, publishing an event — register here. The session provider runs
them after a successful commit, so a worker never races an uncommitted row and
a rolled-back request never triggers them.
"""

from collections.abc import Awaitable, Callable

AfterCommitCallback = Callable[[], Awaitable[None]]


class AfterCommitQueue:
    """Collects callbacks to run after the unit of work commits."""

    def __init__(self) -> None:
        self._callbacks: list[AfterCommitCallback] = []

    def add(self, callback: AfterCommitCallback) -> None:
        """Register a callback to run once the transaction has committed."""
        self._callbacks.append(callback)

    async def run(self) -> None:
        """Run every registered callback in registration order, then clear."""
        callbacks, self._callbacks = self._callbacks, []
        for callback in callbacks:
            await callback()
