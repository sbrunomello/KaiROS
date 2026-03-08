"""LLM provider abstractions and OpenRouter implementation."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    content: str
    model_used: str
    status: str = "ok"
    error_message: str | None = None


class LLMProvider(Protocol):
    def generate(self, messages: list[dict], settings: object) -> LLMResult:
        ...


class OpenRouterProvider:
    def __init__(self) -> None:
        self.config = get_config()

    def generate(self, messages: list[dict], settings: object) -> LLMResult:
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        if settings.http_referer:
            headers["HTTP-Referer"] = settings.http_referer
        if settings.x_title:
            headers["X-Title"] = settings.x_title

        payload = {
            "model": settings.model_name,
            "messages": messages,
            "temperature": settings.temperature,
        }
        with httpx.Client(timeout=self.config.openrouter_timeout_seconds) as client:
            response = client.post(f"{self.config.openrouter_base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        model_used = data.get("model", settings.model_name)
        return LLMResult(content=content, model_used=model_used)


class MockProvider:
    """Deterministic fake provider used in automated tests."""

    def generate(self, messages: list[dict], settings: object) -> LLMResult:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return LLMResult(content=f"Mock resposta: {last_user}", model_used=settings.model_name)


class ResilientLLMService:
    """Wrap provider with retries and user-safe fallback error response."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.config = get_config()

    def generate(self, messages: list[dict], settings: object) -> LLMResult:
        attempts = max(1, self.config.llm_retry_attempts)
        last_error = "Erro desconhecido"
        for attempt in range(1, attempts + 1):
            try:
                return self.provider.generate(messages, settings)
            except Exception as exc:  # noqa: BLE001 - resilience boundary
                last_error = str(exc)
                logger.warning("LLM request failed (attempt %s/%s): %s", attempt, attempts, last_error)
        return LLMResult(
            content="Desculpe, não consegui responder agora. Verifique as configurações e tente novamente.",
            model_used=getattr(settings, "model_name", "unknown"),
            status="error",
            error_message=last_error,
        )
