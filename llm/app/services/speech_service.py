from __future__ import annotations

import logging

from ..providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)


class SpeechService:
    def __init__(self, registry: ProviderRegistry | None = None):
        self.registry = registry or ProviderRegistry()

    def transcribe(self, audio_path: str, settings: object) -> dict[str, str]:
        options = settings.__dict__.copy()
        provider = self.registry.resolve_speech(settings)
        provider_name = getattr(settings, "speech_provider", "groq")
        try:
            result = provider.transcribe(audio_path, options)
            logger.info("speech_transcription_ok provider=%s model=%s", provider_name, result.model_used)
            return {"text": result.text, "model": result.model_used, "provider": provider_name}
        except Exception as exc:  # noqa: BLE001
            logger.error("speech_transcription_error provider=%s error=%s", provider_name, str(exc))
            raise
