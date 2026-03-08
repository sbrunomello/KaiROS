"""Build context window and final prompt payload for the provider."""
from ..config import get_config


class PromptService:
    def __init__(self) -> None:
        self.config = get_config()

    def build_messages(self, system_prompt: str, history: list[dict], user_input: str) -> list[dict]:
        trimmed_history = history[-self.config.context_window_messages :]
        return [{"role": "system", "content": system_prompt}, *trimmed_history, {"role": "user", "content": user_input}]
