from __future__ import annotations

import base64
from pathlib import Path


class ImageInputEncoderError(ValueError):
    """Error raised when uploaded image input is invalid."""


class ImageInputEncoder:
    """Validates and converts local images to provider-compatible data URLs."""

    SUPPORTED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}

    def validate_mime_type(self, mime_type: str) -> str:
        if mime_type not in self.SUPPORTED_MIME_TYPES:
            raise ImageInputEncoderError("Formato de imagem não suportado.")
        return mime_type

    def enforce_size_limit(self, *, image_bytes: bytes, max_size_mb: int) -> None:
        max_bytes = max_size_mb * 1024 * 1024
        if len(image_bytes) > max_bytes:
            raise ImageInputEncoderError("Arquivo de imagem excede o limite permitido.")

    def to_data_url(self, *, image_bytes: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def to_openrouter_input_image(self, *, image_bytes: bytes, mime_type: str) -> dict[str, str]:
        """Build official multimodal image content part for OpenRouter chat/completions."""
        data_url = self.to_data_url(image_bytes=image_bytes, mime_type=mime_type)
        return {"type": "image_url", "image_url": {"url": data_url}}

    def infer_extension(self, mime_type: str) -> str:
        return {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(mime_type, ".bin")

    def validate_file_for_path(self, *, path: Path, mime_type: str, max_size_mb: int) -> bytes:
        self.validate_mime_type(mime_type)
        raw = path.read_bytes()
        self.enforce_size_limit(image_bytes=raw, max_size_mb=max_size_mb)
        return raw
