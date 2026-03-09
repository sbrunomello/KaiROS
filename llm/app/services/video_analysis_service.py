from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import Settings
from .openrouter_client import OpenRouterClient
from .video_input_encoder import VideoInputEncoder


@dataclass
class VideoAnalysisResult:
    text: str
    model: str
    reasoning_details: Any


class VideoAnalysisService:
    """Orquestra o payload multimodal de vídeo para chat completions do OpenRouter."""

    def __init__(self, client: OpenRouterClient | None = None, encoder: VideoInputEncoder | None = None):
        self.client = client or OpenRouterClient()
        self.encoder = encoder or VideoInputEncoder()

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
        video_data_url = self.encoder.build_data_url(raw_bytes=raw_bytes, mime_type=content_type, filename=filename)
        payload = self.build_payload(
            model=model,
            prompt=prompt,
            video_data_url=video_data_url,
            reasoning_enabled=reasoning_enabled,
        )

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
        if content is None:
            raise ValueError("O provider não retornou resposta válida.")

        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            text = "\n".join([part for part in text_parts if part]).strip()
        else:
            text = ""

        if not text:
            raise ValueError("O provider não retornou resposta válida.")

        reasoning_details = response.get("reasoning_details") or message.get("reasoning_details")
        return VideoAnalysisResult(text=text, model=model, reasoning_details=reasoning_details)
