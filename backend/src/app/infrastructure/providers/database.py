"""DI wiring for the SQLAlchemy engine, session factory, and per-request session.

The session provider is the unit-of-work boundary: it commits on success, rolls
back on failure, and only then runs after-commit callbacks (e.g. enqueuing a
background job). Handlers and repositories therefore never commit themselves.
"""

from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.infrastructure.config.settings import AppSettings, get_settings
from app.infrastructure.database.after_commit import AfterCommitQueue
from app.infrastructure.database.engine import build_engine, build_session_factory


class DatabaseProvider(Provider):
    """Engine and factory are singletons; sessions are request-scoped Units of Work."""

    @provide(scope=Scope.APP)
    def settings(self) -> AppSettings:
        return get_settings()

    @provide(scope=Scope.APP)
    def engine(self, settings: AppSettings) -> AsyncEngine:
        return build_engine(settings)

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return build_session_factory(engine)

    after_commit = provide(AfterCommitQueue, scope=Scope.REQUEST)

    @provide(scope=Scope.REQUEST)
    async def session(
        self,
        factory: async_sessionmaker[AsyncSession],
        after_commit: AfterCommitQueue,
    ) -> AsyncIterable[AsyncSession]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        await after_commit.run()
