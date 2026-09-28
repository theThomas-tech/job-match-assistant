"""App settings, read from environment variables or the .env file at the repo root."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    # Looks for .env in the repo root (when run from backend/) or the current folder.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://jobmatch:jobmatch@localhost:5432/jobmatch"
    companies_file: Path = BACKEND_DIR / "companies.yaml"

    # Which AI model provider to use. Only "ollama" (free, runs locally) is built so far.
    llm_provider: Literal["ollama"] = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    # Local models on CPU are slow: allow a long wait before giving up.
    llm_timeout_seconds: float = 900

    anthropic_api_key: str = ""


settings = Settings()
