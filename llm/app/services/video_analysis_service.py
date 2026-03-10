from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import Settings
from ..providers.registry import ProviderRegistry
from .llm_service import ResilientLLMService
from .openrouter_client import OpenRouterClient
from .speech_service import SpeechService
from .video_input_encoder import VideoInputEncoder

logger = logging.getLogger(__name__)


@dataclass
class VideoAnalysisResult:
    text: str
    model: str
    reasoning_details: Any


class AudioExtractionService:
    def extract(self, video_path: str, ffmpeg_binary_path: str = "ffmpeg") -> str:
        audio_path = f"{video_path}.wav"
        cmd = [ffmpeg_binary_path, "-y", "-i", video_path, "-ac", "1", "-ar", "16000", audio_path]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise ValueError(f"Falha ao extrair áudio com ffmpeg: {proc.stderr.strip() or proc.stdout.strip()}")
        return audio_path


class FrameSamplingService:
    def sample(self, video_path: str, interval_seconds: int, ffmpeg_binary_path: str = "ffmpeg") -> list[str]:
        frame_dir = Path(f"{video_path}_frames")
        frame_dir.mkdir(parents=True, exist_ok=True)
        output_pattern = frame_dir / "frame_%03d.jpg"
        cmd = [
            ffmpeg_binary_path,
            "-y",
            "-i",
            video_path,
            "-vf",
            f"fps=1/{max(1, interval_seconds)}",
            str(output_pattern),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise ValueError(f"Falha ao extrair frames: {proc.stderr.strip() or proc.stdout.strip()}")
        return [str(path) for path in sorted(frame_dir.glob("*.jpg"))]


class VideoAnalysisService:
    """Video analysis service with legacy OpenRouter mode and pipeline mode."""

    def __init__(self, client: OpenRouterClient | None = None, encoder: VideoInputEncoder | None = None, registry: ProviderRegistry | None = None):
        self.client = client or OpenRouterClient()
        self.encoder = encoder or VideoInputEncoder()
        self.registry = registry or ProviderRegistry()
        self.audio_extractor = AudioExtractionService()
        self.frame_sampler = FrameSamplingService()

    def build_payload(self, *, model: str, prompt: str, video_data_url: str, reasoning_enabled: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "video_url", "video_url": {"url": video_data_url}},
                    ],
                }
            ],
        }
        if reasoning_enabled:
            payload["reasoning"] = {"enabled": True}
        return payload

    def analyze(
        self,
        *,
        settings: Settings,
        model: str,
        prompt: str,
        filename: str,
        content_type: str,
        raw_bytes: bytes,
        reasoning_enabled: bool,
    ) -> VideoAnalysisResult:
        if (settings.video_analysis_mode or "legacy").lower() == "pipeline":
            return self._analyze_pipeline(settings=settings, prompt=prompt, filename=filename, raw_bytes=raw_bytes)
        return self._analyze_legacy(
            settings=settings,
            model=model,
            prompt=prompt,
            filename=filename,
            content_type=content_type,
            raw_bytes=raw_bytes,
            reasoning_enabled=reasoning_enabled,
        )

    def _analyze_legacy(self, *, settings: Settings, model: str, prompt: str, filename: str, content_type: str, raw_bytes: bytes, reasoning_enabled: bool) -> VideoAnalysisResult:
        video_data_url = self.encoder.build_data_url(raw_bytes=raw_bytes, mime_type=content_type, filename=filename)
        payload = self.build_payload(model=model, prompt=prompt, video_data_url=video_data_url, reasoning_enabled=reasoning_enabled)
        response = self.client.chat_completion(
            api_key=settings.openrouter_api_key,
            payload=payload,
            http_referer=settings.http_referer,
            x_title=settings.x_title,
        )
        choices = response.get("choices") or []
        if not choices:
            raise ValueError("O provider não retornou resposta válida.")

        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            text = "\n".join([part.get("text", "") for part in content if isinstance(part, dict)]).strip()
        else:
            text = ""
        if not text:
            raise ValueError("O provider não retornou resposta válida.")
        return VideoAnalysisResult(text=text, model=model, reasoning_details=response.get("reasoning_details") or message.get("reasoning_details"))

    def _analyze_pipeline(self, *, settings: Settings, prompt: str, filename: str, raw_bytes: bytes) -> VideoAnalysisResult:
        temp_dir = Path(tempfile.mkdtemp(prefix="video-pipeline-"))
        video_path = temp_dir / filename
        video_path.write_bytes(raw_bytes)
        audio_path = None
        frames: list[str] = []
        try:
            audio_path = self.audio_extractor.extract(str(video_path), settings.ffmpeg_binary_path)
            speech_result = SpeechService(registry=self.registry).transcribe(audio_path, settings)
            transcript = speech_result["text"]

            visual_context = ""
            if settings.video_enable_vision:
                try:
                    frames = self.frame_sampler.sample(str(video_path), settings.video_frame_sample_seconds, settings.ffmpeg_binary_path)
                    frame_notes = []
                    primary_name = (settings.vision_provider or "groq").lower()
                    providers = [(primary_name, self.registry.resolve_vision(settings))]
                    fallback_name = (settings.vision_fallback_provider or "").lower()
                    fallback = self.registry.resolve_vision_fallback(settings)
                    if fallback and fallback_name != primary_name:
                        providers.append((fallback_name, fallback))

                    for frame in frames[:5]:
                        for provider_name, vision_provider in providers:
                            try:
                                vision = vision_provider.describe(frame, "Descreva pontos importantes do frame.", settings.__dict__.copy())
                                if vision.text:
                                    frame_notes.append(vision.text)
                                if provider_name != primary_name:
                                    logger.warning("video_pipeline_vision_fallback_triggered primary=%s fallback=%s", primary_name, provider_name)
                                break
                            except Exception as vision_exc:  # noqa: BLE001
                                logger.warning("video_pipeline_frame_vision_error provider=%s error=%s", provider_name, str(vision_exc))
                    visual_context = "\n".join(frame_notes).strip()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("video_pipeline_vision_failed error=%s", str(exc))

            final_prompt = f"{prompt}\n\nTranscrição:\n{transcript}"
            if visual_context:
                final_prompt += f"\n\nContexto visual:\n{visual_context}"
            messages = [{"role": "user", "content": final_prompt}]
            chat_result = ResilientLLMService(self.registry).generate(messages, settings)
            if chat_result.status != "ok":
                raise ValueError(chat_result.error_message or "Falha no chat da análise de vídeo")
            return VideoAnalysisResult(text=chat_result.content, model=chat_result.model_used, reasoning_details={"mode": "pipeline"})
        finally:
            if audio_path:
                Path(audio_path).unlink(missing_ok=True)
            for frame in frames:
                Path(frame).unlink(missing_ok=True)
            frame_dir = Path(f"{video_path}_frames")
            if frame_dir.exists():
                shutil.rmtree(frame_dir, ignore_errors=True)
            shutil.rmtree(temp_dir, ignore_errors=True)
