"""App settings, read from environment variables or the .env file at the repo root."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Looks for .env in the repo root (when run from backend/) or the current folder.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://jobmatch:jobmatch@localhost:5432/jobmatch"
    anthropic_api_key: str = ""


settings = Settings()
