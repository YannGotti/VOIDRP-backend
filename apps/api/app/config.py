from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VoidRP Account API"
    api_v1_prefix: str = "/api/v1"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = True

    database_url: str = Field(
        default="postgresql+psycopg://voidrp:voidrp_password@localhost:5432/voidrp_accounts"
    )

    jwt_secret_key: str = Field(default="CHANGE_ME_TO_LONG_RANDOM_SECRET", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    email_token_expire_hours: int = 24

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    email_from: str = "noreply@void-rp.ru"
    email_backend: Literal["logging"] = "logging"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_dev(self) -> bool:
        return self.app_env in {"development", "test"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
