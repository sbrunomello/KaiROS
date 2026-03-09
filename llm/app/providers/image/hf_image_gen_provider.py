from __future__ import annotations

import httpx

from ..base import ImageResult


class HFImageGenProvider:
    def __init__(self, base_url: str = "https://api-inference.huggingface.co/models"):
        self.base_url = base_url

    def generate(self, prompt: str, options: dict) -> ImageResult:
        api_key = options.get("huggingface_api_key", "")
        model = options.get("hf_default_image_model") or options.get("default_image_model") or "black-forest-labs/FLUX.1-schnell"
        if not api_key:
            raise ValueError("Hugging Face API key não configurada")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"inputs": prompt}
        with httpx.Client(timeout=options.get("request_timeout_seconds", 60)) as client:
            response = client.post(f"{self.base_url}/{model}", headers=headers, json=payload)
            response.raise_for_status()
            mime = response.headers.get("content-type", "image/png").split(";")[0]
            return ImageResult(image_bytes=response.content, mime_type=mime, model_used=model, text="")
