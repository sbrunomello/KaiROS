"""Dependency factories for routes."""
import os

from .services.llm_service import MockProvider, OpenRouterProvider, ResilientLLMService


def get_llm_service() -> ResilientLLMService:
    provider_name = os.getenv("LLM_PROVIDER", "openrouter").lower()
    provider = MockProvider() if provider_name == "mock" else OpenRouterProvider()
    return ResilientLLMService(provider)
