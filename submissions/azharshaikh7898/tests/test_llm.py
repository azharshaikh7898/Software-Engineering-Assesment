from types import SimpleNamespace

import httpx
import openai
import pytest
from tenacity import wait_none

from app import llm


def make_client(fail_times: int, counter: dict):
    class Completions:
        def create(self, **kwargs):
            counter["n"] += 1
            if counter["n"] <= fail_times:
                raise openai.APIConnectionError(request=httpx.Request("POST", "https://llm.test"))
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok [1]"))],
                usage=SimpleNamespace(prompt_tokens=5, completion_tokens=2),
            )

    return SimpleNamespace(chat=SimpleNamespace(completions=Completions()))


def test_transient_errors_are_retried(monkeypatch):
    counter = {"n": 0}
    monkeypatch.setattr(llm, "_get_client", lambda: make_client(2, counter))
    monkeypatch.setattr(llm._call.retry, "wait", wait_none())
    result = llm.complete("system", "user")
    assert counter["n"] == 3 and result.text == "ok [1]" and result.prompt_tokens == 5


def test_persistent_failure_raises_llm_error_after_three_attempts(monkeypatch):
    counter = {"n": 0}
    monkeypatch.setattr(llm, "_get_client", lambda: make_client(99, counter))
    monkeypatch.setattr(llm._call.retry, "wait", wait_none())
    with pytest.raises(llm.LLMError):
        llm.complete("system", "user")
    assert counter["n"] == 3
