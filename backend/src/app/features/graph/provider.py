"""DI provider for the graph CRUD slice."""

from dishka import Provider, Scope, provide

from app.features.graph.repository import Neo4jGraphRepository


class GraphProvider(Provider):
    scope = Scope.REQUEST
    repository = provide(Neo4jGraphRepository)
