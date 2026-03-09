from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .chat.groq_chat_provider import GroqChatProvider
from .chat.openrouter_chat_provider import OpenRouterChatProvider
from .image.hf_image_edit_provider import HFImageEditProvider
from .image.hf_image_gen_provider import HFImageGenProvider
from .speech.groq_speech_provider import GroqSpeechProvider
from .speech.local_whisper_provider import LocalWhisperProvider
from .vision.groq_vision_provider import GroqVisionProvider


class ProviderRegistry:
    """Small provider registry resolved by runtime settings."""

    def __init__(self):
        self.chat_providers = {
            "groq": GroqChatProvider(),
            "openrouter": OpenRouterChatProvider(),
        }
        self.speech_providers = {
            "groq": GroqSpeechProvider(),
            "local": LocalWhisperProvider(),
        }
        self.vision_providers = {"groq": GroqVisionProvider()}
        self.image_gen_providers = {
            "hf": HFImageGenProvider(),
        }
        self.image_edit_providers = {
            "hf": HFImageEditProvider(),
        }

    def chat_provider_name(self, settings: Any) -> str:
        return (getattr(settings, "chat_provider", "groq") or "groq").lower()

    def resolve_chat(self, settings: Any):
        name = self.chat_provider_name(settings)
        return self.chat_providers.get(name) or self.chat_providers["openrouter"]

    def resolve_chat_fallback(self, settings: Any):
        fallback = (getattr(settings, "chat_fallback_provider", "openrouter") or "").lower()
        if not fallback:
            return None
        return self.chat_providers.get(fallback)

    def resolve_speech(self, settings: Any):
        name = (getattr(settings, "speech_provider", "groq") or "groq").lower()
        provider = self.speech_providers.get(name)
        if not provider:
            raise ValueError(f"Speech provider não suportado: {name}")
        return provider

    def resolve_vision(self, settings: Any):
        name = (getattr(settings, "vision_provider", "groq") or "groq").lower()
        provider = self.vision_providers.get(name)
        if not provider:
            raise ValueError(f"Vision provider não suportado: {name}")
        return provider

    def resolve_image_gen(self, settings: Any):
        name = (getattr(settings, "image_gen_provider", "openrouter") or "openrouter").lower()
        provider = self.image_gen_providers.get(name)
        if not provider:
            raise ValueError(f"Image gen provider não suportado: {name}")
        return provider

    def resolve_image_edit(self, settings: Any):
        name = (getattr(settings, "image_edit_provider", "hf") or "hf").lower()
        provider = self.image_edit_providers.get(name)
        if not provider:
            raise ValueError(f"Image edit provider não suportado: {name}")
        return provider

    @staticmethod
    def provider_options(settings: Any) -> dict[str, Any]:
        return asdict(settings) if hasattr(settings, "__dataclass_fields__") else settings.__dict__.copy()
