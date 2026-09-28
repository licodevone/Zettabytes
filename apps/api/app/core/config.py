from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, PostgresDsn, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = API_DIR.parents[1]


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Configuração central. Lê variáveis de ambiente e, em dev, o `.env` da raiz do monorepo."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", API_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Zettabytes API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    API_V1_PREFIX: str = "/api/v1"

    # ─── Banco de dados ──────────────────────────────────────
    DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://zettabytes:zettabytes@localhost:5442/zettabytes"
    )
    TEST_DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://zettabytes:zettabytes@localhost:5442/zettabytes_test"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE_SECONDS: int = 1800
    DB_ECHO: bool = False

    # ─── Segurança / JWT ─────────────────────────────────────
    JWT_SECRET_KEY: SecretStr = SecretStr("dev-insecure-secret-change-me-" + "x" * 32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "zettabytes"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    # Chave Fernet para criptografar segredos em repouso (tokens da Meta).
    ENCRYPTION_KEY: SecretStr | None = None

    # ─── HTTP ────────────────────────────────────────────────
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3100"]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                import json

                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _secret_min_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY deve ter pelo menos 32 caracteres")
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def database_url(self) -> str:
        url = self.TEST_DATABASE_URL if self.ENVIRONMENT == Environment.TEST else self.DATABASE_URL
        return str(url)

    def validate_for_production(self) -> None:
        """Falha cedo (no boot) se a configuração não for segura para produção."""
        if not self.is_production:
            return
        if self.JWT_SECRET_KEY.get_secret_value().startswith(("dev-insecure", "change-me")):
            raise RuntimeError("Defina JWT_SECRET_KEY em produção.")
        if self.ENCRYPTION_KEY is None:
            raise RuntimeError("Defina ENCRYPTION_KEY em produção.")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
