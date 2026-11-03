from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    test_database_url: str | None = None
    secret_key: str = Field(min_length=32)
    algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    cors_origins: list[str] = Field(default_factory=list)
    environment: Literal["dev", "test", "prod"] = "dev"

    @model_validator(mode="after")
    def reject_wildcard_in_production(self):
        if self.environment == "prod" and "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS no puede contener '*' en producción")
        return self

    @property
    def active_database_url(self) -> str:
        if self.environment == "test" and self.test_database_url:
            return self.test_database_url
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
