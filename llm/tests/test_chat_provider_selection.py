from types import SimpleNamespace

from llm.app.providers.registry import ProviderRegistry
from llm.app.services.llm_service import ResilientLLMService


class OkProvider:
    def __init__(self, text: str, model: str):
        self.text = text
        self.model = model

    def generate(self, messages, options):
        from llm.app.providers.base import ChatResult

        return ChatResult(content=self.text, model_used=self.model)


class FailingProvider:
    def generate(self, messages, options):
        raise ValueError("boom")


def test_resilient_llm_service_uses_primary_provider():
    registry = ProviderRegistry()
    registry.chat_providers["groq"] = OkProvider("ok", "groq-model")
    service = ResilientLLMService(registry)
    settings = SimpleNamespace(chat_provider="groq", chat_fallback_provider="openrouter", chat_model_name="x")

    result = service.generate([{"role": "user", "content": "oi"}], settings)
    assert result.status == "ok"
    assert result.model_used == "groq-model"


def test_resilient_llm_service_fallback_on_error():
    registry = ProviderRegistry()
    registry.chat_providers["groq"] = FailingProvider()
    registry.chat_providers["openrouter"] = OkProvider("fallback", "openrouter-model")
    service = ResilientLLMService(registry)
    settings = SimpleNamespace(chat_provider="groq", chat_fallback_provider="openrouter", chat_model_name="x")

    result = service.generate([{"role": "user", "content": "oi"}], settings)
    assert result.status == "ok"
    assert result.content == "fallback"
