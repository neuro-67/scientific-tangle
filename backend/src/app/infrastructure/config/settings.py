"""Environment-driven application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    """Postgres connection settings."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    host: str = "postgres"
    port: int = 5432
    user: str = "st"
    password: str = "st_password"
    db: str = "scientific_tangle"

    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class Neo4jSettings(BaseSettings):
    """Neo4j connection settings."""

    model_config = SettingsConfigDict(env_prefix="NEO4J_", extra="ignore")

    uri: str = "bolt://neo4j:7687"
    user: str = "neo4j"
    password: str = "neo4j_password"


class QdrantSettings(BaseSettings):
    """Qdrant connection settings."""

    model_config = SettingsConfigDict(env_prefix="QDRANT_", extra="ignore")

    host: str = "qdrant"
    http_port: int = 6333
    grpc_port: int = 6334


class MinioSettings(BaseSettings):
    """MinIO / S3-compatible object storage settings."""

    model_config = SettingsConfigDict(env_prefix="MINIO_", extra="ignore")

    endpoint: str = "minio:9000"
    root_user: str = "minioadmin"
    root_password: str = "minioadmin"
    secure: bool = False
    documents_bucket: str = "documents"


class RedisSettings(BaseSettings):
    """Redis connection settings (backing the arq job queue)."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")

    host: str = "redis"
    port: int = 6379
    database: int = 0


class JwtSettings(BaseSettings):
    """JWT signing settings."""

    model_config = SettingsConfigDict(env_prefix="JWT_", extra="ignore")

    secret: str = "change_me"
    algorithm: str = "HS256"
    access_ttl_minutes: int = 30
    refresh_ttl_days: int = 14


class CookieSettings(BaseSettings):
    """httpOnly cookie transport for access/refresh JWTs."""

    model_config = SettingsConfigDict(env_prefix="COOKIE_", extra="ignore")

    access_name: str = "st_access"
    refresh_name: str = "st_refresh"
    domain: str | None = None
    secure: bool = False  # flip to True when serving over HTTPS
    samesite: Literal["lax", "strict", "none"] = "lax"
    refresh_path: str = "/auth"


class CorsSettings(BaseSettings):
    """CORS whitelist for the SPA frontend."""

    model_config = SettingsConfigDict(env_prefix="CORS_", extra="ignore")

    # Comma-separated in env: `CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:3000`
    allow_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allow_origins.split(",") if o.strip()]


class LlmSettings(BaseSettings):
    """LLM API settings."""

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")

    api_key: str = ""
    model: str = ""


class AdminSeedSettings(BaseSettings):
    """Credentials for the initial admin created by the seed CLI."""

    model_config = SettingsConfigDict(env_prefix="ADMIN_", extra="ignore")

    username: str = "admin"
    password: str = ""
    full_name: str = "Platform Administrator"


class AppSettings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(extra="ignore")

    env: str = Field(default="dev", alias="APP_ENV")
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    minio: MinioSettings = Field(default_factory=MinioSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    jwt: JwtSettings = Field(default_factory=JwtSettings)
    cookies: CookieSettings = Field(default_factory=CookieSettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    admin_seed: AdminSeedSettings = Field(default_factory=AdminSeedSettings)


@lru_cache
def get_settings() -> AppSettings:
    """Return a cached AppSettings instance."""
    return AppSettings()
