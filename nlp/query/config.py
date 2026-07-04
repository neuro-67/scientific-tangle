"""Environment-driven configuration for the query pipeline.

All fields have defaults so the class can be instantiated without env vars.
Callers must set api_key and folder_id before use.
"""

from __future__ import annotations

import os


class QueryConfig:
    """Settings loaded from environment variables with safe defaults.

    Provider selection: RouterAI is preferred when configured (Yandex Studio
    has been down), Yandex is used if only that key is set, otherwise the
    caller falls back to the rule-based parser.
    """

    def __init__(self) -> None:
        self.yandex_api_key: str = os.environ.get("YANDEX_API_KEY", "")
        self.yandex_folder_id: str = os.environ.get("YANDEX_FOLDER_ID", "")
        self.yandex_base_url: str = os.environ.get(
            "YANDEX_BASE_URL", "https://llm.api.cloud.yandex.net"
        )
        self.yandex_model: str = os.environ.get("YANDEX_MODEL", "yandexgpt-5.1")
        self.yandex_temperature: float = float(os.environ.get("YANDEX_TEMPERATURE", "0.1"))
        self.yandex_max_tokens: int = int(os.environ.get("YANDEX_MAX_TOKENS", "2000"))

        self.routerai_api_key: str = os.environ.get("ROUTERAI_API_KEY", "")
        self.routerai_base_url: str = os.environ.get(
            "ROUTERAI_BASE_URL", "https://routerai.ru/api/v1"
        )
        # gemini-3.1-flash-lite: fastest of the models benchmarked (parse ~3.3s,
        # synthesis ~4.1s) -- both parse and synthesis sit on the live 3-5s SLA
        # path (docs/ARCHITECTURE.md), so speed dominates over extraction
        # richness here (unlike ingestion, which uses qwen3-30b-a3b instead).
        self.routerai_model: str = os.environ.get("ROUTERAI_MODEL", "google/gemini-3.1-flash-lite")
        self.routerai_temperature: float = float(os.environ.get("ROUTERAI_TEMPERATURE", "0.1"))
        self.routerai_max_tokens: int = int(os.environ.get("ROUTERAI_MAX_TOKENS", "2000"))

    @property
    def provider(self) -> str:
        if self.routerai_api_key:
            return "routerai"
        if self.yandex_api_key:
            return "yandex"
        return "none"
