"""DI provider for the query parser (YandexGPT adapter)."""

from dishka import Provider, Scope, provide

from app.domain.interfaces.query_parser import IQueryParser
from app.infrastructure.config.settings import AppSettings
from nlp.query.parser import QuerySpecParser
from nlp.query.config import QueryConfig


class YandexQueryParser(IQueryParser):
    """Wraps the ML-2 QuerySpecParser so it satisfies the domain port."""

    def __init__(self, config: QueryConfig) -> None:
        self._parser = QuerySpecParser(config)

    def parse(self, question: str):
        return self._parser.parse(question)


class QueryParserProvider(Provider):
    """Wires the YandexGPT-based query parser as a singleton."""

    scope = Scope.APP

    @provide
    def query_parser(self, settings: AppSettings) -> IQueryParser:
        config = QueryConfig()
        config.yandex_api_key = settings.llm.api_key
        # Folder ID may come from env or settings; fallback to empty
        config.yandex_folder_id = getattr(settings.llm, "folder_id", "")
        if settings.llm.model:
            config.yandex_model = settings.llm.model
        return YandexQueryParser(config)
