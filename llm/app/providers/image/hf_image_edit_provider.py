from __future__ import annotations

from pathlib import Path

import httpx

from ..base import ImageResult


class HFImageEditProvider:
    # Endpoint oficial dos Inference Providers da Hugging Face.
    # Referência: https://huggingface.co/docs/api-inference/index
    def __init__(self, base_url: str = "https://router.huggingface.co/hf-inference/models"):
        self.base_url = base_url.rstrip("/")

    def edit(self, image_path: str, prompt: str, options: dict) -> ImageResult:
        if not options.get("image_edit_enabled", False):
            raise ValueError("image->image desabilitado por configuração (image_edit_enabled=false)")
        api_key = options.get("huggingface_api_key", "")
        if not api_key:
            raise ValueError("Hugging Face API key não configurada")
        model = options.get("image_edit_model_name") or options.get("hf_default_image_model") or options.get("default_image_model")
        if not model:
            raise ValueError("Modelo de edição de imagem não configurado")

        image_bytes = Path(image_path).read_bytes()
        headers = {"Authorization": f"Bearer {api_key}"}
        files = {"image": (Path(image_path).name, image_bytes)}
        data = {"prompt": prompt}
        with httpx.Client(timeout=options.get("request_timeout_seconds", 60)) as client:
            try:
                response = client.post(f"{self.base_url}/{model}", headers=headers, data=data, files=files)
                response.raise_for_status()
            except httpx.TimeoutException as exc:
                raise ValueError("Timeout ao chamar Hugging Face Inference API para editar imagem") from exc
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
