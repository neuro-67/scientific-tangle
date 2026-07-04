"""DI provider for the cross-encoder reranker."""

from dishka import Provider, Scope, provide

from app.domain.interfaces.reranker import IReranker
from nlp.reranker.cross_encoder import CrossEncoderReranker


class CrossEncoderRerankerAdapter(IReranker):
    """Wraps the ML-2 CrossEncoderReranker so it satisfies the domain port."""

    def __init__(self) -> None:
        self._reranker = CrossEncoderReranker()

    def rerank(self, query: str, results: list[dict], top_k: int = 10) -> list[dict]:
        return self._reranker.rerank(query, results, top_k)


class RerankerProvider(Provider):
    """Wires the cross-encoder reranker as a singleton."""

    scope = Scope.APP

    @provide
    def reranker(self) -> IReranker:
        return CrossEncoderRerankerAdapter()
