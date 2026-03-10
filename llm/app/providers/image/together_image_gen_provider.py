from __future__ import annotations

import base64

import httpx

from ..base import ImageResult


class TogetherImageGenProvider:
    def __init__(self, base_url: str = "https://api.together.xyz/v1"):
        self.base_url = base_url

    def generate(self, prompt: str, options: dict) -> ImageResult:
        api_key = options.get("together_api_key", "")
        if not api_key:
            raise ValueError("Together API key não configurada")
        model = options.get("together_default_image_model") or options.get("default_image_model")

        payload = {"model": model, "prompt": prompt, "response_format": "b64_json"}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=options.get("request_timeout_seconds", 60)) as client:
            response = client.post(f"{self.base_url}/images/generations", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        image_b64 = ((data.get("data") or [{}])[0]).get("b64_json")
        if not image_b64:
            raise ValueError("Together não retornou imagem")
        return ImageResult(image_bytes=base64.b64decode(image_b64), mime_type="image/png", model_used=model)
