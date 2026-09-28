"""Get a validated Pydantic object out of a model, and log every attempt to the llm_calls table."""

from pydantic import BaseModel, ValidationError
from sqlmodel import Session

from app.llm.base import LLMProvider
from app.models import LLMCall


class LLMOutputError(Exception):
    """The model didn't produce a valid answer, even after retrying."""


def generate_structured[T: BaseModel](
    session: Session,
    provider: LLMProvider,
    *,
    output_model: type[T],
    system: str,
    user: str,
    purpose: str,
    prompt_version: str,
    max_attempts: int = 2,
) -> T:
    """Call the model and parse its JSON answer into `output_model`.

    If the answer doesn't match the schema, retry once, telling the model what was wrong.
    Every attempt (success or failure) is recorded in llm_calls for the cost/quality page.
    """
    if not user.strip():
        # A model given nothing will happily invent an answer, so never call it with empty input.
        raise ValueError("Refusing to call the model with empty input")

    schema = output_model.model_json_schema()
    prompt = user
    last_error = ""
    for _ in range(max_attempts):
        call = LLMCall(
            provider=provider.name,
            model=provider.model,
            purpose=purpose,
            prompt_version=prompt_version,
        )
        try:
            result = provider.complete_json(system, prompt, schema)
            call.model = result.model
            call.input_tokens = result.input_tokens
            call.output_tokens = result.output_tokens
            call.latency_ms = result.latency_ms
            call.cost_usd = provider.cost_usd(result)
            parsed = output_model.model_validate_json(result.text)
            call.success = True
            return parsed
        except ValidationError as exc:
            last_error = f"Answer didn't match the schema: {exc.errors(include_url=False)[:3]}"
            call.error = last_error
            prompt = f"{user}\n\nYour previous answer was invalid ({last_error}). Answer again."
        except Exception as exc:  # network errors, timeouts, model not found...
            call.error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            session.add(call)
            session.commit()

    raise LLMOutputError(last_error)
