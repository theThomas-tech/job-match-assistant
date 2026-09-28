"""Ollama: free models that run on this computer. Docs: https://docs.ollama.com/api"""

import json
import time

import httpx

from app.llm.base import LLMResult


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str, base_url: str, timeout: float) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete_json(self, system: str, user: str, schema: dict) -> LLMResult:
        body = {
            "model": self.model,
            "stream": False,
            # Ollama constrains the output to this JSON Schema, so the reply is always valid JSON.
            "format": schema,
            "options": {
                # Ollama's default context window is small and silently cuts off long inputs.
                "num_ctx": 8192,
                "num_predict": 2048,  # stop runaway answers
                "temperature": 0,  # same input -> same output, which makes evals repeatable
            },
            "messages": [
                # `format` only restricts the output; the model can't see it. Show it the
                # schema too, so it knows what each field means.
                {
                    "role": "system",
                    "content": f"{system}\n\nAnswer with JSON matching this schema:\n{json.dumps(schema)}",
                },
                {"role": "user", "content": user},
            ],
        }
        started = time.perf_counter()
        response = httpx.post(f"{self.base_url}/api/chat", json=body, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return LLMResult(
            text=data["message"]["content"],
            model=self.model,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            latency_ms=round((time.perf_counter() - started) * 1000),
        )

    def cost_usd(self, result: LLMResult) -> float:
        return 0.0
