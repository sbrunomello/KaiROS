"""Centralized runtime configuration for the standalone LLM web app."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Environment-driven app configuration with safe defaults for Orange Pi."""

    app_name: str = "KaiROS LLM Chat"
    host: str = "0.0.0.0"
    port: int = 8091
    debug: bool = False

    base_dir: Path = Path(__file__).resolve().parents[1]
    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1] / "data")
    db_path: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1] / "data" / "llm.db")

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: int = 25
    max_message_chars: int = 8000
    context_window_messages: int = 12
    llm_retry_attempts: int = 2
    fallback_models: str = ""

    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    cfg = AppConfig()
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    return cfg
