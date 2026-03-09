from types import SimpleNamespace

import pytest

from llm.app.providers.registry import ProviderRegistry


def test_registry_resolves_chat_provider():
    settings = SimpleNamespace(chat_provider="groq", chat_fallback_provider="openrouter")
    registry = ProviderRegistry()
    provider = registry.resolve_chat(settings)
    assert provider.__class__.__name__ == "GroqChatProvider"
    assert registry.resolve_chat_fallback(settings).__class__.__name__ == "OpenRouterChatProvider"


def test_registry_invalid_speech_provider_raises():
    settings = SimpleNamespace(speech_provider="unknown")
    registry = ProviderRegistry()
    with pytest.raises(ValueError):
        registry.resolve_speech(settings)
