from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Any

from ...services.image_input_encoder import ImageInputEncoder
from ...services.openrouter_client import OpenRouterClient
from ..base import ImageResult


class OpenRouterImageEditProvider:
    def __init__(self, client: OpenRouterClient | None = None):
        self.client = client or OpenRouterClient()
        self.encoder = ImageInputEncoder()

    def edit(self, image_path: str, prompt: str, options: dict[str, Any]) -> ImageResult:
        data_url = self.encoder.to_data_url(Path(image_path).read_bytes(), "image/png")
        payload = {
            "model": options.get("openrouter_default_image_model") or options.get("default_image_model") or "bytedance-seed/seedream-4.5",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "modalities": ["image"],
        }
        response = self.client.chat_completion(
            api_key=options.get("openrouter_api_key", ""),
            payload=payload,
            http_referer=options.get("http_referer", ""),
            x_title=options.get("x_title", ""),
        )
        model_used = response.get("model", payload["model"])
        image_url = self._extract_data_url(response)
        mime_type, image_bytes = self._decode_data_url(image_url)
        return ImageResult(image_bytes=image_bytes, mime_type=mime_type, model_used=model_used)

    def _extract_data_url(self, data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("Resposta inválida do provider: sem choices")
        message = (choices[0] or {}).get("message") or {}
        images = message.get("images") or []
        if not images:
            raise ValueError("Modelo não retornou imagens")
        first_image = images[0] or {}
        image_url_payload = first_image.get("image_url")
        image_url = image_url_payload.get("url") if isinstance(image_url_payload, dict) else image_url_payload
        if not isinstance(image_url, str) or not image_url.startswith("data:image/"):
            raise ValueError("Resposta inválida do provider: image_url ausente")
        return image_url

    def _decode_data_url(self, image_url: str) -> tuple[str, bytes]:
        header, b64data = image_url.split(",", 1)
        mime_type = header.split(";")[0].replace("data:", "")
        try:
            image_bytes = base64.b64decode(b64data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Falha ao decodificar imagem retornada") from exc
        return mime_type, image_bytes
