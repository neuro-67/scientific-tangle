"""Environment-driven configuration for the query pipeline.

All fields have defaults so the class can be instantiated without env vars.
Callers must set api_key and folder_id before use.
"""

from __future__ import annotations

import os


class QueryConfig:
    """Settings loaded from environment variables with safe defaults."""

    def __init__(self) -> None:
        self.yandex_api_key: str = os.environ.get("YANDEX_API_KEY", "")
        self.yandex_folder_id: str = os.environ.get("YANDEX_FOLDER_ID", "")
        self.yandex_base_url: str = os.environ.get(
            "YANDEX_BASE_URL", "https://llm.api.cloud.yandex.net"
        )
        self.yandex_model: str = os.environ.get("YANDEX_MODEL", "yandexgpt-5.1")
        self.yandex_temperature: float = float(os.environ.get("YANDEX_TEMPERATURE", "0.1"))
        self.yandex_max_tokens: int = int(os.environ.get("YANDEX_MAX_TOKENS", "2000"))
