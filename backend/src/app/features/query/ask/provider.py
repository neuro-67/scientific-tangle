"""DI provider for the ask-question slice."""

from dishka import Provider, Scope, provide

from app.features.query.ask.handler import AskQuestionHandler


class AskQuestionProvider(Provider):
    """Wires the ask-question handler. Dependencies (parser, graph_search, vector_search, synthesis)
    are provided by other providers (QueryParserProvider, Neo4jProvider, QdrantProvider, SynthesisProvider)."""

    scope = Scope.REQUEST

    handler = provide(AskQuestionHandler)
