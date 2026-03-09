"""Standalone FastAPI app entrypoint for llm chat subproject."""
from sqlalchemy import text
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_config
from .db import Base, engine
from .logging_conf import setup_logging
from .routes import api_chat, api_chats, api_health, api_settings, web

config = get_config()
setup_logging(config.debug)
Base.metadata.create_all(bind=engine)


def _ensure_username_column() -> None:
    """Add username column for legacy SQLite databases without migrations."""
    with engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(conversations)")).fetchall()
        column_names = {column[1] for column in columns}
        if "username" not in column_names:
            conn.execute(text("ALTER TABLE conversations ADD COLUMN username VARCHAR(64) DEFAULT 'default'"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_conversations_username ON conversations (username)"))


_ensure_username_column()

app = FastAPI(title=config.app_name)
app.mount("/static", StaticFiles(directory="llm/app/static"), name="static")

app.include_router(web.router)
app.include_router(api_health.router)
app.include_router(api_chats.router)
app.include_router(api_chat.router)
app.include_router(api_settings.router)
