from __future__ import annotations

import base64
import mimetypes


class VideoInputEncoderError(ValueError):
    """Erro de validação/codificação de vídeo para input multimodal."""


class VideoInputEncoder:
    """Valida uploads de vídeo e converte para Data URL base64 aceito pelo OpenRouter."""

    allowed_mime_types = {"video/mp4", "video/webm", "video/quicktime"}

    def validate_presence(self, raw_bytes: bytes | None) -> None:
        if not raw_bytes:
            raise VideoInputEncoderError("Adicione um vídeo para análise.")

    def validate_mime_type(self, mime_type: str) -> None:
        if mime_type not in self.allowed_mime_types:
            raise VideoInputEncoderError("Formato de vídeo não suportado.")

    def validate_size_limit(self, *, raw_bytes: bytes, max_size_mb: int) -> None:
        max_bytes = max_size_mb * 1024 * 1024
        if len(raw_bytes) > max_bytes:
            raise VideoInputEncoderError("O arquivo excede o limite permitido.")

    def build_data_url(self, *, raw_bytes: bytes, mime_type: str, filename: str = "") -> str:
        self.validate_presence(raw_bytes)
        detected_mime = mime_type or mimetypes.guess_type(filename or "")[0] or "video/mp4"
        self.validate_mime_type(detected_mime)
        encoded = base64.b64encode(raw_bytes).decode("utf-8")
        return f"data:{detected_mime};base64,{encoded}"
