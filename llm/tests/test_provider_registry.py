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


def test_registry_resolves_new_chat_and_vision_providers():
    registry = ProviderRegistry()
    settings = SimpleNamespace(
        chat_provider="deepinfra",
        vision_provider="cloudflare",
        image_gen_provider="together",
        vision_fallback_provider="openrouter",
        image_gen_fallback_provider="hf",
    )
    assert registry.resolve_chat(settings).__class__.__name__ == "DeepInfraChatProvider"
    assert registry.resolve_vision(settings).__class__.__name__ == "CloudflareVisionProvider"
    assert registry.resolve_image_gen(settings).__class__.__name__ == "TogetherImageGenProvider"
    assert registry.resolve_vision_fallback(settings).__class__.__name__ == "OpenRouterVisionProvider"
    assert registry.resolve_image_gen_fallback(settings).__class__.__name__ == "HFImageGenProvider"
