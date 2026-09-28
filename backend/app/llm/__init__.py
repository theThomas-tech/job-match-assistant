"""AI model access. Everything else in the app calls get_provider() and generate_structured()."""

from app.config import settings
from app.llm.base import LLMProvider, LLMResult
from app.llm.ollama import OllamaProvider
from app.llm.structured import LLMOutputError, generate_structured


def get_provider() -> LLMProvider:
    """The provider chosen in .env (LLM_PROVIDER). Also used as a FastAPI dependency."""
    if settings.llm_provider == "ollama":
        return OllamaProvider(
            model=settings.ollama_model,
            base_url=settings.ollama_url,
            timeout=settings.llm_timeout_seconds,
        )
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


__all__ = ["LLMOutputError", "LLMProvider", "LLMResult", "generate_structured", "get_provider"]
