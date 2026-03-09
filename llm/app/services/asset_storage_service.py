from __future__ import annotations

from pathlib import Path
from uuid import uuid4


class AssetStorageService:
    """Handles local persistence of generated and input multimodal assets."""

    EXTENSION_BY_MIME = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
    }

    def __init__(self, base_dir: Path, public_prefix: str = "/generated-images") -> None:
        self.base_dir = base_dir
        self.public_prefix = public_prefix.rstrip("/")

    def _save_bytes(self, *, raw_bytes: bytes, mime_type: str, filename_prefix: str) -> dict[str, str | int]:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        extension = self.EXTENSION_BY_MIME.get(mime_type, ".bin")
        filename = f"{filename_prefix}_{uuid4().hex}{extension}"
        output_path = self.base_dir / filename
        output_path.write_bytes(raw_bytes)
        return {
            "file_path": str(output_path),
            "public_url": f"{self.public_prefix}/{filename}",
            "mime_type": mime_type,
            "size_bytes": len(raw_bytes),
        }

    def save_input_image(self, *, image_bytes: bytes, mime_type: str, filename_prefix: str = "input") -> dict[str, str | int]:
        return self._save_bytes(raw_bytes=image_bytes, mime_type=mime_type, filename_prefix=filename_prefix)

    def save_input_video(self, *, video_bytes: bytes, mime_type: str, filename_prefix: str = "video") -> dict[str, str | int]:
        return self._save_bytes(raw_bytes=video_bytes, mime_type=mime_type, filename_prefix=filename_prefix)

    def save_generated_image(self, *, image_bytes: bytes, mime_type: str) -> dict[str, str | int]:
        return self._save_bytes(raw_bytes=image_bytes, mime_type=mime_type, filename_prefix="img")
