import logging
from dataclasses import dataclass

import openai
from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from .config import settings

log = logging.getLogger("documind.llm")

_RETRYABLE = (openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError)


class LLMError(Exception):
    """The language model could not produce an answer (after retries)."""


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.llm_api_key:
            raise LLMError("LLM_API_KEY is not configured")
        _client = OpenAI(
            base_url=settings.llm_base_url, api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_s, max_retries=0,  # retries are handled by tenacity below
        )
    return _client


@retry(
    retry=retry_if_exception_type(_RETRYABLE),  # timeouts are APIConnectionError subclasses
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(min=1, max=8),
    reraise=True,
)
def _call(messages: list[dict]):
    return _get_client().chat.completions.create(
        model=settings.llm_model, messages=messages, temperature=0, max_tokens=600
    )


def complete(system: str, user: str) -> LLMResult:
    try:
        resp = _call([{"role": "system", "content": system}, {"role": "user", "content": user}])
    except LLMError:
        raise
    except openai.OpenAIError as exc:
        log.warning("LLM call failed after retries", extra={"extra_fields": {"error": type(exc).__name__}})
        raise LLMError(type(exc).__name__) from exc
    usage = resp.usage
    return LLMResult(
        text=resp.choices[0].message.content or "",
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
    )
