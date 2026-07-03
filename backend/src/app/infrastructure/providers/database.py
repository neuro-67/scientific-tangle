"""DI wiring for the SQLAlchemy engine, session factory, and per-request session."""

from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.infrastructure.config.settings import AppSettings, get_settings
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

    @provide(scope=Scope.REQUEST)
    async def session(
        self,
        factory: async_sessionmaker[AsyncSession],
    ) -> AsyncIterable[AsyncSession]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
