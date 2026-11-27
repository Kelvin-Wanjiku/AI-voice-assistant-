import re
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables or backend/.env"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Milo"
    frontend_origin: str = "http://localhost:5173"
    database_url: str = ""

    # Milo's brain. See llm.py for the providers you can choose from.
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: str = ""  # leave empty to use the provider's default model
    llm_reasoning_effort: str = ""  # leave empty to use the provider's default

    # If a look-up takes longer than this (seconds), Milo says "let me check" so there's no long silence.
    holding_after_seconds: float = 3.0

    # Web search (optional). Free key from https://app.tavily.com
    tavily_api_key: str = ""

    @field_validator("holding_after_seconds", mode="before")
    @classmethod
    def read_seconds(cls, value):
        """Accept "3", "3.5", "40s", "40 sec" or "40 seconds"."""
        if isinstance(value, str):
            match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*(s|sec|secs|second|seconds)?\s*", value.lower())
            if not match:
                raise ValueError(
                    f"HOLDING_AFTER_SECONDS in backend/.env should be a number of seconds, like 3. It says \"{value}\"."
                )
            return float(match.group(1).replace(",", "."))
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
