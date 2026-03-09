from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import httpx

from ..base import VisionResult


class GroqVisionProvider:
    def __init__(self, base_url: str = "https://api.groq.com/openai/v1"):
        self.base_url = base_url

    def describe(self, image_path: str, prompt: str, options: dict) -> VisionResult:
        api_key = options.get("groq_api_key", "")
        if not api_key:
            raise ValueError("Groq API key não configurada")
        model = options.get("vision_model_name") or options.get("chat_model_name")
        if not model:
            raise ValueError("Modelo de vision não configurado")

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
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=options.get("request_timeout_seconds", 60)) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
        return VisionResult(text=str(content).strip(), model_used=data.get("model", model))
