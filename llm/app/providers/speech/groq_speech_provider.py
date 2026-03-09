from __future__ import annotations

from pathlib import Path

import httpx

from ..base import SpeechResult


class GroqSpeechProvider:
    def __init__(self, base_url: str = "https://api.groq.com/openai/v1"):
        self.base_url = base_url

    def transcribe(self, audio_path: str, options: dict) -> SpeechResult:
        api_key = options.get("groq_api_key", "")
        if not api_key:
            raise ValueError("Groq API key não configurada")
        model = options.get("speech_model_name", "whisper-large-v3-turbo")
        path = Path(audio_path)
        if not path.exists():
            raise ValueError("Arquivo de áudio não encontrado")

        with path.open("rb") as audio_file:
            files = {"file": (path.name, audio_file, "audio/wav")}
            data = {"model": model}
            headers = {"Authorization": f"Bearer {api_key}"}
            with httpx.Client(timeout=options.get("request_timeout_seconds", 60)) as client:
                response = client.post(f"{self.base_url}/audio/transcriptions", headers=headers, data=data, files=files)
                response.raise_for_status()
                payload = response.json()

        return SpeechResult(text=payload.get("text", "").strip(), model_used=model)
