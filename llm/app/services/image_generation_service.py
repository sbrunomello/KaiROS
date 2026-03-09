from __future__ import annotations

import base64
import binascii
from typing import Any

from ..models import Settings
from .asset_storage_service import AssetStorageService
from .image_input_encoder import ImageInputEncoder
from .openrouter_client import OpenRouterClient


class ImageGenerationError(ValueError):
    """Represents validation/extraction/storage errors for image generation."""


class ImageGenerationService:
    def __init__(
        self,
        client: OpenRouterClient | None = None,
        generated_storage: AssetStorageService | None = None,
        input_storage: AssetStorageService | None = None,
        input_encoder: ImageInputEncoder | None = None,
    ):
        self.client = client or OpenRouterClient()
        if generated_storage is None:
            raise ValueError("AssetStorageService de saída é obrigatório para salvar imagens localmente")
        self.generated_storage = generated_storage
        self.input_storage = input_storage
        self.input_encoder = input_encoder or ImageInputEncoder()

    def build_payload(
        self,
        *,
        model: str,
        prompt: str,
        mode: str = "text_to_image",
        input_image_data_url: str | None = None,
    ) -> dict[str, Any]:
        if mode == "image_to_image":
            if not input_image_data_url:
                raise ImageGenerationError("Adicione uma imagem para usar o modo imagem para imagem.")
            return {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": input_image_data_url}},
                        ],
                    }
                ],
                "modalities": ["image"],
            }

        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image"],
        }

    def generate(
        self,
        *,
        settings: Settings,
        model: str,
        prompt: str,
        mode: str = "text_to_image",
        input_image_bytes: bytes | None = None,
        input_image_mime_type: str | None = None,
    ) -> dict[str, Any]:
        input_image_url = ""
        input_image_data_url = None

        if mode == "image_to_image":
            if not input_image_bytes or not input_image_mime_type:
                raise ImageGenerationError("Adicione uma imagem para usar o modo imagem para imagem.")
            self.input_encoder.validate_mime_type(input_image_mime_type)
            input_image_data_url = self.input_encoder.to_data_url(image_bytes=input_image_bytes, mime_type=input_image_mime_type)
            if self.input_storage:
                saved_input = self.input_storage.save_input_image(
                    image_bytes=input_image_bytes,
                    mime_type=input_image_mime_type,
                    filename_prefix="input",
                )
                input_image_url = str(saved_input["public_url"])

        payload = self.build_payload(model=model, prompt=prompt, mode=mode, input_image_data_url=input_image_data_url)
        response = self.client.chat_completion(
            api_key=settings.openrouter_api_key,
            payload=payload,
            http_referer=settings.http_referer,
            x_title=settings.x_title,
        )
        image_data_url = self._extract_data_url(response)
        mime_type, image_bytes = self._decode_data_url(image_data_url)
        saved_asset = self.generated_storage.save_generated_image(image_bytes=image_bytes, mime_type=mime_type)

        return {
            "image_url": saved_asset["public_url"],
            "file_path": saved_asset["file_path"],
            "mime_type": saved_asset["mime_type"],
            "size_bytes": saved_asset["size_bytes"],
            "text": self._extract_text(response),
            "input_image_url": input_image_url,
        }

    def _extract_text(self, data: dict[str, Any]) -> str:
        message = ((data.get("choices") or [{}])[0]).get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") in ("text", "output_text"):
                    return part.get("text", "")
        return ""

    def _extract_data_url(self, data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise ImageGenerationError("Resposta inválida do provider: sem choices")

        message = (choices[0] or {}).get("message") or {}
        images = message.get("images") or []
        if not images:
            raise ImageGenerationError("Modelo não retornou imagens")

        first_image = images[0] or {}
        image_url_payload = first_image.get("image_url")
        image_url = image_url_payload.get("url") if isinstance(image_url_payload, dict) else image_url_payload

        if not isinstance(image_url, str) or not image_url:
            raise ImageGenerationError("Resposta inválida do provider: image_url ausente")
        if not image_url.startswith("data:image/"):
            raise ImageGenerationError("Resposta inválida do provider: image_url não é data URL")
        return image_url

    def _decode_data_url(self, image_url: str) -> tuple[str, bytes]:
        try:
            header, b64data = image_url.split(",", 1)
        except ValueError as exc:
            raise ImageGenerationError("Resposta inválida do provider: data URL malformada") from exc

        mime_type = header.split(";")[0].replace("data:", "")
        try:
            image_bytes = base64.b64decode(b64data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ImageGenerationError("Falha ao decodificar imagem retornada.") from exc

        return mime_type, image_bytes
