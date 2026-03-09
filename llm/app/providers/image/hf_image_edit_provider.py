from __future__ import annotations

from pathlib import Path

import httpx

from ..base import ImageResult


class HFImageEditProvider:
    def __init__(self, base_url: str = "https://api-inference.huggingface.co/models"):
        self.base_url = base_url

    def edit(self, image_path: str, prompt: str, options: dict) -> ImageResult:
        if not options.get("image_edit_enabled", False):
            raise ValueError("image->image desabilitado por configuração (image_edit_enabled=false)")
        api_key = options.get("huggingface_api_key", "")
        if not api_key:
            raise ValueError("Hugging Face API key não configurada")
        model = options.get("image_edit_model_name") or options.get("default_image_model")
        if not model:
            raise ValueError("Modelo de edição de imagem não configurado")

        image_bytes = Path(image_path).read_bytes()
        headers = {"Authorization": f"Bearer {api_key}"}
        files = {"image": (Path(image_path).name, image_bytes)}
        data = {"prompt": prompt}
        with httpx.Client(timeout=options.get("request_timeout_seconds", 60)) as client:
            response = client.post(f"{self.base_url}/{model}", headers=headers, data=data, files=files)
            response.raise_for_status()
        mime = response.headers.get("content-type", "image/png").split(";")[0]
        return ImageResult(image_bytes=response.content, mime_type=mime, model_used=model, text="")
