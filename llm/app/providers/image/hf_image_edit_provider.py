from __future__ import annotations

from pathlib import Path

import base64

import httpx

from ..base import ImageResult


class HFImageEditProvider:
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

    def _build_request_payload(self, image_path: str, prompt: str, endpoint: str):
        """Monta payload conforme tipo de endpoint: legacy multipart ou provider JSON/base64."""
        image_bytes = Path(image_path).read_bytes()
        # Endpoints de provider custom via router usam payload JSON com base64 em `inputs`.
        if "router.huggingface.co" in endpoint and "/hf-inference/models/" not in endpoint:
            body = {
                "inputs": base64.b64encode(image_bytes).decode("utf-8"),
                "parameters": {"prompt": prompt},
            }
            return {"json": body}

        files = {"image": (Path(image_path).name, image_bytes)}
        data = {"prompt": prompt}
        return {"data": data, "files": files}

    def edit(self, image_path: str, prompt: str, options: dict) -> ImageResult:
        if not options.get("image_edit_enabled", False):
            raise ValueError("image->image desabilitado por configuração (image_edit_enabled=false)")
        api_key = options.get("huggingface_api_key", "")
        if not api_key:
            raise ValueError("Hugging Face API key não configurada")
        model = options.get("image_edit_model_name") or options.get("hf_default_image_model") or options.get("default_image_model")
        endpoint_override = (options.get("hf_image_edit_endpoint") or "").strip()
        target = endpoint_override or model
        if not target:
            raise ValueError("Modelo/endpoint de edição de imagem não configurado")

        headers = {"Authorization": f"Bearer {api_key}"}
        endpoint = self._build_endpoint(target)
        request_payload = self._build_request_payload(image_path, prompt, endpoint)
        with httpx.Client(timeout=options.get("request_timeout_seconds", 60)) as client:
            try:
                response = client.post(endpoint, headers=headers, **request_payload)
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
        model_used = endpoint_override or model
        return ImageResult(image_bytes=response.content, mime_type=mime, model_used=model_used, text="")
