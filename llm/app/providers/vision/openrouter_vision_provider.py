from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from ...services.openrouter_client import OpenRouterClient
from ..base import VisionResult


class OpenRouterVisionProvider:
    def __init__(self, client: OpenRouterClient | None = None):
        self.client = client or OpenRouterClient()

    def describe(self, image_path: str, prompt: str, options: dict) -> VisionResult:
        api_key = options.get("openrouter_api_key", "")
        if not api_key:
            raise ValueError("OpenRouter API key não configurada")
        model = options.get("vision_model_name") or options.get("model_name") or "openrouter/auto"

        path = Path(image_path)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
        data_url = f"data:{mime};base64,{b64}"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or "Descreva esta imagem."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        }
        data = self.client.chat_completion(
            api_key=api_key,
            payload=payload,
            http_referer=options.get("http_referer", ""),
            x_title=options.get("x_title", ""),
        )
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
        return VisionResult(text=str(content).strip(), model_used=data.get("model", model))
