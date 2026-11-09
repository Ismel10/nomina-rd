"""Configuración desde variables de entorno (ver .env.example en la raíz del repo)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str | None = None
    cors_origins: str = "http://localhost:5173"

    payroll_country: str = "DO"
    default_currency: str = "DOP"
    default_locale: str = "es-DO"
    timezone: str = "America/Santo_Domingo"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
