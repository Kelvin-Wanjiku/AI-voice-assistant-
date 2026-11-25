from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
