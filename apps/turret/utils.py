"""Helpers pequenos e reutilizáveis."""


def clamp(value: float, low: float, high: float) -> float:
    """Limita value para o intervalo [low, high]."""
    return max(low, min(high, value))
