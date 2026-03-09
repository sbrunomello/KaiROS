"""Dependency factories for routes."""
import os
import re

from fastapi import Header, HTTPException, Query

from .providers.registry import ProviderRegistry
from .services.llm_service import MockProvider, ResilientLLMService

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")


class MockResilientService:
    def __init__(self):
        self.provider = MockProvider()

    def generate(self, messages: list[dict], settings: object):
        return self.provider.generate(messages, settings)


def get_llm_service() -> ResilientLLMService | MockResilientService:
    provider_name = os.getenv("LLM_PROVIDER", "registry").lower()
    if provider_name == "mock":
        return MockResilientService()
    return ResilientLLMService(ProviderRegistry())


def get_username(
    username_query: str | None = Query(default=None, alias="username"),
    username_header: str | None = Header(default=None, alias="X-Username"),
) -> str:
    """Resolve and validate the username for local user isolation."""
    username = (username_header or username_query or "default").strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(
            status_code=422,
            detail="username inválido: use 3-32 caracteres com letras, números, '_' ou '-'",
        )
    return username
