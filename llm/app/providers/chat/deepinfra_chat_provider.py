from __future__ import annotations

from typing import Any

import httpx

from ..base import ChatResult


class DeepInfraChatProvider:
    def __init__(self, base_url: str = "https://api.deepinfra.com/v1/openai"):
        self.base_url = base_url

    def generate(self, messages: list[dict[str, Any]], options: dict[str, Any]) -> ChatResult:
        api_key = options.get("deepinfra_api_key", "")
        if not api_key:
            raise ValueError("DeepInfra API key não configurada")
        model = options.get("deepinfra_default_chat_model") or options.get("chat_model_name")
        if not model:
            raise ValueError("Modelo de chat da DeepInfra não configurado")

        payload = {"model": model, "messages": messages, "temperature": options.get("temperature", 0.7)}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=options.get("request_timeout_seconds", 30)) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        return ChatResult(content=content, model_used=data.get("model", model))
