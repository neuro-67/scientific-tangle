"""DI provider for Neo4j driver and graph-search adapter."""

from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.domain.interfaces.graph_search import IGraphSearch
from app.infrastructure.config.settings import AppSettings
from app.infrastructure.neo4j.graph_search import Neo4jGraphSearch


class Neo4jProvider(Provider):
    """Wires the Neo4j async driver and the graph-search port."""

    @provide(scope=Scope.APP)
    async def neo4j_driver(self, settings: AppSettings) -> AsyncIterable[AsyncDriver]:
        driver = AsyncGraphDatabase.driver(
            settings.neo4j.uri,
            auth=(settings.neo4j.user, settings.neo4j.password),
        )
        try:
            yield driver
        finally:
            await driver.close()

    @provide(scope=Scope.REQUEST)
    def graph_search(self, driver: AsyncDriver) -> IGraphSearch:
        return Neo4jGraphSearch(driver)
