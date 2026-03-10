from __future__ import annotations

import base64

import httpx

from ..base import ImageResult


class CloudflareImageGenProvider:
    def generate(self, prompt: str, options: dict) -> ImageResult:
        token = options.get("cloudflare_api_token", "")
        account_id = options.get("cloudflare_account_id", "")
        if not token or not account_id:
            raise ValueError("Cloudflare API token/account_id não configurados")

        model = options.get("cloudflare_default_image_model") or "@cf/stabilityai/stable-diffusion-xl-base-1.0"
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"prompt": prompt}
        with httpx.Client(timeout=options.get("request_timeout_seconds", 60)) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        image_b64 = (data.get("result") or {}).get("image")
        if not image_b64:
            raise ValueError("Cloudflare não retornou imagem")
        return ImageResult(image_bytes=base64.b64decode(image_b64), mime_type="image/png", model_used=model)
