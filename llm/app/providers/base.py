from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ChatResult:
    content: str
    model_used: str


@dataclass
class SpeechResult:
    text: str
    model_used: str


@dataclass
class VisionResult:
    text: str
    model_used: str


@dataclass
class ImageResult:
    image_bytes: bytes
    mime_type: str
    model_used: str
    text: str = ""


class ChatProvider(Protocol):
    def generate(self, messages: list[dict[str, Any]], options: dict[str, Any]) -> ChatResult:
        ...


class SpeechProvider(Protocol):
    def transcribe(self, audio_path: str, options: dict[str, Any]) -> SpeechResult:
        ...


class VisionProvider(Protocol):
    def describe(self, image_path: str, prompt: str, options: dict[str, Any]) -> VisionResult:
        ...


class ImageGenProvider(Protocol):
    def generate(self, prompt: str, options: dict[str, Any]) -> ImageResult:
        ...


class ImageEditProvider(Protocol):
    def edit(self, image_path: str, prompt: str, options: dict[str, Any]) -> ImageResult:
        ...
