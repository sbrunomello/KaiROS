from __future__ import annotations

from typing import Any

import httpx

from ..base import ChatResult


class CloudflareChatProvider:
    def generate(self, messages: list[dict[str, Any]], options: dict[str, Any]) -> ChatResult:
        token = options.get("cloudflare_api_token", "")
        account_id = options.get("cloudflare_account_id", "")
        if not token or not account_id:
            raise ValueError("Cloudflare API token/account_id não configurados")

        model = options.get("cloudflare_default_chat_model") or options.get("chat_model_name")
        if not model:
            raise ValueError("Modelo de chat da Cloudflare não configurado")

        payload = {"model": model, "messages": messages, "temperature": options.get("temperature", 0.7)}
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions"

        with httpx.Client(timeout=options.get("request_timeout_seconds", 30)) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data["result"]["response"] if "result" in data else data["choices"][0]["message"]["content"]
        return ChatResult(content=str(content), model_used=model)
