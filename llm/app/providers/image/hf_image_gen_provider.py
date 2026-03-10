from __future__ import annotations

import httpx

from ..base import ImageResult


class HFImageGenProvider:
    # Endpoint oficial dos Inference Providers da Hugging Face.
    # Referência: https://huggingface.co/docs/api-inference/index
    def __init__(self, base_url: str = "https://router.huggingface.co/hf-inference/models"):
        self.base_url = base_url.rstrip("/")

    def _build_endpoint(self, model_or_url: str) -> str:
        """Aceita id de modelo (legacy) ou URL completa do provider HF Router."""
        target = (model_or_url or "").strip()
        if target.startswith(("http://", "https://")):
            return target
        return f"{self.base_url}/{target}"

    def generate(self, prompt: str, options: dict) -> ImageResult:
        api_key = options.get("huggingface_api_key", "")
        model = options.get("hf_default_image_model") or options.get("default_image_model") or "black-forest-labs/FLUX.1-schnell"
        if not api_key:
            raise ValueError("Hugging Face API key não configurada")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"inputs": prompt}
        with httpx.Client(timeout=options.get("request_timeout_seconds", 60)) as client:
            try:
                endpoint = self._build_endpoint(model)
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
            except httpx.TimeoutException as exc:
                raise ValueError("Timeout ao chamar Hugging Face Inference API para gerar imagem") from exc
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code == 410:
                    raise ValueError(
                        f"Modelo do Hugging Face indisponível (410 Gone): {model}. "
                        "Atualize o modelo padrão nas configurações."
                    ) from exc
                raise ValueError(f"Hugging Face retornou erro HTTP {status_code} para o modelo {model}") from exc
            except httpx.HTTPError as exc:
                raise ValueError("Falha de rede ao chamar Hugging Face Inference API") from exc

            mime = response.headers.get("content-type", "image/png").split(";")[0]
            return ImageResult(image_bytes=response.content, mime_type=mime, model_used=model, text="")
