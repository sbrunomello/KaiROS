from __future__ import annotations

import logging

from ..providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)


class SpeechService:
    def __init__(self, registry: ProviderRegistry | None = None):
        self.registry = registry or ProviderRegistry()

    def transcribe(self, audio_path: str, settings: object) -> dict[str, str]:
        options = settings.__dict__.copy()
        primary_name = (getattr(settings, "speech_provider", "groq") or "groq").lower()
        primary = self.registry.resolve_speech(settings)

        try:
            result = primary.transcribe(audio_path, options)
            logger.info("speech_transcription_ok provider=%s model=%s", primary_name, result.model_used)
            return {"text": result.text, "model": result.model_used, "provider": primary_name}
        except Exception as primary_exc:  # noqa: BLE001
            logger.warning("speech_transcription_primary_failed provider=%s error=%s", primary_name, str(primary_exc))
            if primary_name != "groq":
                raise

            try:
                local = self.registry.speech_providers["local"]
                fallback_result = local.transcribe(audio_path, options)
                logger.info(
                    "speech_transcription_fallback_ok primary=%s fallback=local model=%s",
                    primary_name,
                    fallback_result.model_used,
                )
                return {"text": fallback_result.text, "model": fallback_result.model_used, "provider": "local"}
            except Exception as fallback_exc:  # noqa: BLE001
                logger.error(
                    "speech_transcription_fallback_failed primary=%s fallback=local primary_error=%s fallback_error=%s",
                    primary_name,
                    str(primary_exc),
                    str(fallback_exc),
                )
                raise ValueError(f"Falha no speech primário ({primary_name}) e fallback local: {fallback_exc}") from fallback_exc
