from __future__ import annotations

from typing import Any

from ...services.openrouter_client import OpenRouterClient
from ..base import ChatResult


class OpenRouterChatProvider:
    def __init__(self, client: OpenRouterClient | None = None):
        self.client = client or OpenRouterClient()

    def generate(self, messages: list[dict[str, Any]], options: dict[str, Any]) -> ChatResult:
        payload = {
            "model": options["model_name"],
            "messages": messages,
            "temperature": options.get("temperature", 0.7),
        }
        data = self.client.chat_completion(
            api_key=options.get("openrouter_api_key", ""),
            payload=payload,
            http_referer=options.get("http_referer", ""),
            x_title=options.get("x_title", ""),
        )
        content = data["choices"][0]["message"]["content"]
        model_used = data.get("model", options["model_name"])
        return ChatResult(content=content, model_used=model_used)
