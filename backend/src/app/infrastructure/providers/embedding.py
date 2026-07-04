"""DI provider for the embedding generator."""

from dishka import Provider, Scope, provide

from app.domain.interfaces.embedding_generator import IEmbeddingGenerator
from nlp.embeddings.bge_m3 import BgeEmbeddingGenerator


class BgeEmbeddingGeneratorAdapter(IEmbeddingGenerator):
    """Wraps the ML-2 BgeEmbeddingGenerator so it satisfies the domain port."""

    def __init__(self) -> None:
        self._generator = BgeEmbeddingGenerator()

    def encode(self, text: str) -> list[float]:
        return self._generator.encode(text)


class EmbeddingProvider(Provider):
    """Wires the BAAI/bge-m3 embedding generator as a singleton."""

    scope = Scope.APP

    @provide
    def embedding_generator(self) -> IEmbeddingGenerator:
        return BgeEmbeddingGeneratorAdapter()
