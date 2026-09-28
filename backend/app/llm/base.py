"""The interface every AI model provider implements, so providers can be swapped by config."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResult:
    """The raw answer from one model call, plus what it cost in tokens and time."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class LLMProvider(Protocol):
    name: str  # "ollama", later "anthropic"
    model: str

    def complete_json(self, system: str, user: str, schema: dict) -> LLMResult:
        """Ask the model for a JSON answer that follows `schema` (a JSON Schema)."""
        ...

    def cost_usd(self, result: LLMResult) -> float:
        """What this call cost. Local models are free."""
        ...
