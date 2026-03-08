"""Select primary and fallback models for generation attempts."""
from ..config import get_config


class ModelRouter:
    def __init__(self) -> None:
        self.config = get_config()

    def candidates(self, configured_model: str) -> list[str]:
        models = [configured_model.strip()] if configured_model.strip() else []
        fallback = [m.strip() for m in self.config.fallback_models.split(",") if m.strip()]
        for model in fallback:
            if model not in models:
                models.append(model)
        if not models:
            models = ["openrouter/auto"]
        return models
