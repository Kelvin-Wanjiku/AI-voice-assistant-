"""The only file that talks to the AI provider.

All four supported providers speak the same "OpenAI-compatible" language, so one piece of code
works for all of them. Switching provider is a settings change in backend/.env, not a code change.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

from openai import OpenAI

from app.config import get_settings


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    default_model: str | None
    key_page: str
    reasoning_effort: str | None = None  # "low" keeps thinking models quick


PROVIDERS = {
    "groq": Provider(
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        default_model="openai/gpt-oss-120b",
        key_page="https://console.groq.com/keys",
        reasoning_effort="low",
    ),
    "gemini": Provider(
        name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        default_model="gemini-3.5-flash-lite",
        key_page="https://aistudio.google.com/apikey",
    ),
    "mistral": Provider(
        name="Mistral",
        base_url="https://api.mistral.ai/v1",
        default_model="mistral-small-latest",
        key_page="https://console.mistral.ai/api-keys",
    ),
    "openrouter": Provider(
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        default_model=None,  # free models change often: pick one on openrouter.ai and set LLM_MODEL
        key_page="https://openrouter.ai/keys",
    ),
}


class BrainNotConfigured(Exception):
    """Raised when the settings for Milo's brain are missing or wrong."""


@dataclass(frozen=True)
class BrainSetup:
    provider: Provider
    model: str
    api_key: str
    reasoning_effort: str | None


def current_setup() -> BrainSetup:
    """Read the brain settings from .env and check them. Raises BrainNotConfigured with a helpful message."""
    s = get_settings()
    key = s.llm_provider.strip().lower()
    if key not in PROVIDERS:
        raise BrainNotConfigured(
            f"LLM_PROVIDER '{s.llm_provider}' isn't recognised. Use one of: {', '.join(PROVIDERS)}."
        )
    provider = PROVIDERS[key]
    if not s.llm_api_key.strip():
        raise BrainNotConfigured(f"No API key set. Get one at {provider.key_page} and add LLM_API_KEY to backend/.env.")
    model = s.llm_model.strip() or provider.default_model
    if not model:
        raise BrainNotConfigured(f"{provider.name} needs a model name. Set LLM_MODEL in backend/.env.")
    effort = s.llm_reasoning_effort.strip() or provider.reasoning_effort
    return BrainSetup(provider, model, s.llm_api_key.strip(), effort)


@lru_cache
def get_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key, timeout=30.0, max_retries=1)


THINKING_TAGS = re.compile(r"<think>.*?</think>", re.DOTALL)


def complete(system: str, messages: list[dict], max_tokens: int = 1024) -> str:
    """Send instructions plus a conversation to the AI and return its answer as plain text.

    Used for Milo's replies (chat.py) and for deciding what to remember (memory_keeper.py).
    """
    setup = current_setup()
    client = get_client(setup.provider.base_url, setup.api_key)

    extra = {"reasoning_effort": setup.reasoning_effort} if setup.reasoning_effort else {}
    response = client.chat.completions.create(
        model=setup.model,
        messages=[{"role": "system", "content": system}, *messages],
        max_tokens=max_tokens,  # room for the model's private thinking plus the answer
        **extra,
    )
    text = ""
    if response.choices:
        text = response.choices[0].message.content or ""
    # Some models include their private reasoning in <think> tags; Milo should never say that out loud.
    return THINKING_TAGS.sub("", text).strip()


def complete_or_choose_tools(system: str, messages: list[dict], tools: list[dict]) -> tuple[str, list[tuple[str, str]]]:
    """Ask the AI to either answer straight away, or say which tools it wants to use first.

    Returns (answer text, [(tool name, arguments as JSON text), ...]). Only one of the two is normally filled.
    """
    setup = current_setup()
    client = get_client(setup.provider.base_url, setup.api_key)
    extra = {"reasoning_effort": setup.reasoning_effort} if setup.reasoning_effort else {}
    response = client.chat.completions.create(
        model=setup.model,
        messages=[{"role": "system", "content": system}, *messages],
        tools=tools,
        tool_choice="auto",
        max_tokens=1024,
        **extra,
    )
    if not response.choices:
        return "", []
    message = response.choices[0].message
    calls = [(c.function.name, c.function.arguments or "{}") for c in (getattr(message, "tool_calls", None) or []) if c.function]
    text = THINKING_TAGS.sub("", message.content or "").strip()
    return text, calls
