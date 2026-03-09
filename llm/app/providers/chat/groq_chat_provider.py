from __future__ import annotations

from typing import Any

import httpx

from ...config import get_config
from ..base import ChatResult


class GroqChatProvider:
    def __init__(self, base_url: str = "https://api.groq.com/openai/v1"):
        self.base_url = base_url
        self.config = get_config()

    def generate(self, messages: list[dict[str, Any]], options: dict[str, Any]) -> ChatResult:
        api_key = options.get("groq_api_key", "")
        if not api_key:
            raise ValueError("Groq API key não configurada")
        payload = {
            "model": options["chat_model_name"],
            "messages": messages,
            "temperature": options.get("temperature", 0.7),
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=options.get("request_timeout_seconds", self.config.openrouter_timeout_seconds)) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        return ChatResult(content=content, model_used=data.get("model", options["chat_model_name"]))
