"""DI provider for the synthesis engine (YandexGPT adapter)."""

from dishka import Provider, Scope, provide

from app.domain.interfaces.synthesis_engine import ISynthesisEngine
from app.infrastructure.config.settings import AppSettings
from nlp.synthesis.engine import SynthesisEngine
from nlp.query.config import QueryConfig


class YandexSynthesisEngine(ISynthesisEngine):
    """Wraps the ML-2 SynthesisEngine so it satisfies the domain port."""

    def __init__(self, config: QueryConfig) -> None:
        self._engine = SynthesisEngine(config)

    def synthesize(self, question: str, findings: list[dict]) -> SynthesisResponse:
        return self._engine.synthesize(question, findings)


class SynthesisProvider(Provider):
    """Wires the YandexGPT-based synthesis engine as a singleton."""

    scope = Scope.APP

    @provide
    def synthesis_engine(self, settings: AppSettings) -> ISynthesisEngine:
        config = QueryConfig()
        config.yandex_api_key = settings.llm.api_key
        config.yandex_folder_id = getattr(settings.llm, "folder_id", "")
        if settings.llm.model:
            config.yandex_model = settings.llm.model
        return YandexSynthesisEngine(config)
