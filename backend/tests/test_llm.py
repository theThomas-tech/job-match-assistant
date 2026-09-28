import json

import httpx
import pytest
from sqlmodel import select

from app.llm import LLMOutputError, generate_structured
from app.models import LLMCall
from app.schemas import ResumeProfile
from tests.fakes import PROFILE, FakeProvider

VALID = json.dumps(PROFILE)
INVALID = json.dumps({"headline": "missing every other field"})


def run(session, provider, user="Resume text"):
    return generate_structured(
        session,
        provider,
        output_model=ResumeProfile,
        system="Extract a profile.",
        user=user,
        purpose="resume_profile",
        prompt_version="test_v1",
    )


def logged_calls(session):
    return session.exec(select(LLMCall).order_by(LLMCall.id)).all()


def test_valid_answer_is_parsed_and_logged(session):
    profile = run(session, FakeProvider(VALID))

    [call] = logged_calls(session)
    assert profile.skills[0] == "Python"
    assert call.success is True
    assert (call.purpose, call.prompt_version, call.provider) == ("resume_profile", "test_v1", "fake")
    assert (call.input_tokens, call.output_tokens, call.cost_usd) == (100, 50, 0.001)


def test_invalid_answer_is_retried_with_the_error(session):
    provider = FakeProvider(INVALID, VALID)

    profile = run(session, provider)

    first, second = logged_calls(session)
    assert profile.headline == PROFILE["headline"]
    assert first.success is False and "schema" in first.error
    assert second.success is True
    assert "previous answer was invalid" in provider.prompts[1]


def test_gives_up_after_repeated_invalid_answers(session):
    with pytest.raises(LLMOutputError):
        run(session, FakeProvider(INVALID, INVALID))

    assert [call.success for call in logged_calls(session)] == [False, False]


def test_connection_errors_are_logged_and_raised(session):
    with pytest.raises(httpx.ConnectError):
        run(session, FakeProvider(httpx.ConnectError("refused")))

    [call] = logged_calls(session)
    assert call.success is False
    assert "ConnectError" in call.error


def test_empty_input_never_reaches_the_model(session):
    provider = FakeProvider(VALID)

    with pytest.raises(ValueError):
        run(session, provider, user="   ")

    assert provider.prompts == []
    assert logged_calls(session) == []
