from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import httpx

from ..base import VisionResult


class CloudflareVisionProvider:
    def describe(self, image_path: str, prompt: str, options: dict) -> VisionResult:
        token = options.get("cloudflare_api_token", "")
        account_id = options.get("cloudflare_account_id", "")
        if not token or not account_id:
            raise ValueError("Cloudflare API token/account_id não configurados")

        model = options.get("cloudflare_default_vision_model") or options.get("vision_model_name")
        if not model:
            raise ValueError("Modelo de vision da Cloudflare não configurado")

        path = Path(image_path)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or "Descreva esta imagem."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                }
            ],
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions"
        with httpx.Client(timeout=options.get("request_timeout_seconds", 30)) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        text = data.get("result", {}).get("response")
        if not text:
            text = data["choices"][0]["message"]["content"]
        return VisionResult(text=str(text).strip(), model_used=model)
