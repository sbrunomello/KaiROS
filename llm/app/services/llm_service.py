"""LLM provider abstractions with registry-driven chat provider selection."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from ..providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    content: str
    model_used: str
    status: str = "ok"
    error_message: str | None = None


class MockProvider:
    """Deterministic fake provider used in automated tests."""

    def generate(self, messages: list[dict], settings: object) -> LLMResult:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return LLMResult(content=f"Mock resposta: {last_user}", model_used=getattr(settings, "chat_model_name", "mock"))


class ResilientLLMService:
    """Wrap chat provider with retries, provider fallback and safe user response."""

    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def generate(self, messages: list[dict], settings: object) -> LLMResult:
        options = settings.__dict__.copy()
        primary_name = self.registry.chat_provider_name(settings)
        providers = [(primary_name, self.registry.resolve_chat(settings))]
        fallback = self.registry.resolve_chat_fallback(settings)
        if fallback and getattr(settings, "chat_fallback_provider", "") != primary_name:
            providers.append((getattr(settings, "chat_fallback_provider"), fallback))

        last_error = "Erro desconhecido"
        for provider_name, provider in providers:
            try:
                result = provider.generate(messages, options)
                logger.info("chat_provider_success provider=%s model=%s", provider_name, result.model_used)
                return LLMResult(content=result.content, model_used=result.model_used)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                logger.warning("chat_provider_error provider=%s error=%s", provider_name, last_error)

        return LLMResult(
            content="Desculpe, não consegui responder agora. Verifique as configurações e tente novamente.",
            model_used=getattr(settings, "chat_model_name", "unknown"),
            status="error",
            error_message=last_error,
        )
