"""OpenRouter HTTP client with safe logging and shared request handling."""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self, timeout_seconds: int | None = None) -> None:
        cfg = get_config()
        self.base_url = cfg.openrouter_base_url
        self.timeout_seconds = timeout_seconds or cfg.openrouter_timeout_seconds

    def _headers(self, api_key: str, http_referer: str = "", x_title: str = "") -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if http_referer:
            headers["HTTP-Referer"] = http_referer
        if x_title:
            headers["X-Title"] = x_title
        return headers

    def get_models(self) -> list[dict[str, Any]]:
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(f"{self.base_url}/models")
            response.raise_for_status()
            payload = response.json()
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        models = payload.get("data", [])
        logger.info("openrouter_models_fetched count=%s latency_ms=%s", len(models), elapsed_ms)
        return models

    def chat_completion(self, *, api_key: str, payload: dict[str, Any], http_referer: str = "", x_title: str = "") -> dict[str, Any]:
        if not api_key:
            raise ValueError("OpenRouter API key não configurada")

        headers = self._headers(api_key, http_referer=http_referer, x_title=x_title)
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "openrouter_chat_completion_ok model=%s latency_ms=%s payload_chars=%s",
            payload.get("model"),
            elapsed_ms,
            len(str(payload))
        )
        return data
