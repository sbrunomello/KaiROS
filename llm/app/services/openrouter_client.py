"""OpenRouter HTTP client with safe logging and shared request handling."""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)


class OpenRouterHTTPError(Exception):
    """Structured HTTP error from OpenRouter with sanitized request context."""

    def __init__(
        self,
        *,
        status_code: int,
        url: str,
        request_payload: dict[str, Any],
        response_text: str,
    ) -> None:
        super().__init__(f"OpenRouter HTTP {status_code}: {response_text}")
        self.status_code = status_code
        self.url = url
        self.request_payload = request_payload
        self.response_text = response_text


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
        url = f"{self.base_url}/chat/completions"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                sanitized_payload = self._sanitize_payload(payload)
                logger.error(
                    "openrouter_http_error status=%s url=%s request_payload=%s response_text=%s",
                    exc.response.status_code,
                    str(exc.request.url),
                    sanitized_payload,
                    exc.response.text,
                )
                raise OpenRouterHTTPError(
                    status_code=exc.response.status_code,
                    url=str(exc.request.url),
                    request_payload=sanitized_payload,
                    response_text=exc.response.text,
                ) from exc
            data = response.json()
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "openrouter_chat_completion_ok model=%s latency_ms=%s payload_chars=%s",
            payload.get("model"),
            elapsed_ms,
            len(str(payload))
        )
        return data

    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Removes large/binary blobs from payload logging while preserving structure."""

        def sanitize_value(value: Any) -> Any:
            if isinstance(value, dict):
                sanitized: dict[str, Any] = {}
                for key, item in value.items():
                    if key in {"url", "image_url", "video_url"} and isinstance(item, str) and item.startswith("data:"):
                        sanitized[key] = f"<data_url length={len(item)}>"
                    else:
                        sanitized[key] = sanitize_value(item)
                return sanitized
            if isinstance(value, list):
                return [sanitize_value(item) for item in value]
            return value

        return sanitize_value(payload)
