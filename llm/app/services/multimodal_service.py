from __future__ import annotations

import base64
import mimetypes
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..models import MultimodalHistory, Settings
from .openrouter_client import OpenRouterClient


class ModelCatalogService:
    def __init__(self, client: OpenRouterClient | None = None):
        self.client = client or OpenRouterClient()

    def get_capabilities(self) -> dict[str, Any]:
        models = self.client.get_models()
        mapped = []
        for model in models:
            arch = model.get("architecture") or {}
            mapped.append(
                {
                    "id": model.get("id"),
                    "name": model.get("name", model.get("id")),
                    "input_modalities": arch.get("input_modalities", []),
                    "output_modalities": arch.get("output_modalities", []),
                }
            )
        return {
            "models": mapped,
            "image_models": [m for m in mapped if "image" in m["output_modalities"]],
            "video_input_models": [m for m in mapped if "video" in m["input_modalities"]],
            "video_generation_models": [m for m in mapped if "video" in m["output_modalities"]],
        }


class HistoryService:
    def __init__(self, db: Session):
        self.db = db

    def list(self, username: str) -> list[MultimodalHistory]:
        return self.db.query(MultimodalHistory).filter(MultimodalHistory.username == username).order_by(MultimodalHistory.created_at.desc()).all()

    def add(
        self,
        *,
        username: str,
        item_type: str,
        model_name: str,
        prompt: str,
        status: str,
        response_text: str = "",
        asset_url: str = "",
        metadata_json: str = "",
    ) -> MultimodalHistory:
        item = MultimodalHistory(
            username=username,
            item_type=item_type,
            model_name=model_name,
            prompt=prompt,
            status=status,
            response_text=response_text,
            asset_url=asset_url,
            metadata_json=metadata_json,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item


class ImageGenerationService:
    def __init__(self, client: OpenRouterClient | None = None):
        self.client = client or OpenRouterClient()

    def generate(self, *, settings: Settings, model: str, prompt: str) -> dict[str, str]:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
        }
        data = self.client.chat_completion(
            api_key=settings.openrouter_api_key,
            payload=payload,
            http_referer=settings.http_referer,
            x_title=settings.x_title,
        )
        image_url = self._extract_image_url(data)
        if not image_url:
            raise ValueError("Não foi possível extrair imagem da resposta do modelo")
        text = self._extract_text(data)
        return {"image_url": image_url, "text": text}

    def _extract_text(self, data: dict[str, Any]) -> str:
        message = ((data.get("choices") or [{}])[0]).get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") in ("text", "output_text"):
                    return part.get("text", "")
        return ""

    def _extract_image_url(self, data: dict[str, Any]) -> str | None:
        message = ((data.get("choices") or [{}])[0]).get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") in ("image_url", "output_image"):
                    img = part.get("image_url")
                    if isinstance(img, dict):
                        return img.get("url")
                    if isinstance(img, str):
                        return img
                    return part.get("url")
        if isinstance(message.get("images"), list) and message["images"]:
            first = message["images"][0]
            if isinstance(first, dict):
                return first.get("image_url") or first.get("url")
            if isinstance(first, str):
                return first
        return data.get("image_url")


class VideoAnalysisService:
    allowed_mime_types = {"video/mp4", "video/webm", "video/quicktime"}

    def __init__(self, client: OpenRouterClient | None = None):
        self.client = client or OpenRouterClient()

    def analyze(self, *, settings: Settings, model: str, prompt: str, filename: str, content_type: str, raw_bytes: bytes) -> str:
        if content_type not in self.allowed_mime_types:
            raise ValueError("Formato de vídeo inválido. Use MP4, WEBM ou MOV.")

        guessed = mimetypes.guess_type(filename)[0]
        mime = content_type or guessed or "video/mp4"
        encoded = base64.b64encode(raw_bytes).decode("utf-8")
        data_url = f"data:{mime};base64,{encoded}"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "video_url", "video_url": {"url": data_url}},
                    ],
                }
            ],
        }
        response = self.client.chat_completion(
            api_key=settings.openrouter_api_key,
            payload=payload,
            http_referer=settings.http_referer,
            x_title=settings.x_title,
        )
        message = ((response.get("choices") or [{}])[0]).get("message") or {}
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
        return ""
