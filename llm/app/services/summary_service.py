"""Optional helper for future summarization (placeholder kept lightweight)."""


def summarize_title(first_message: str) -> str:
    return (first_message or "Novo chat").strip()[:60] or "Novo chat"
