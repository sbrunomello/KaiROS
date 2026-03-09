"""Standalone FastAPI app entrypoint for llm chat subproject."""
from sqlalchemy import text
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_config
from .db import Base, engine
from .logging_conf import setup_logging
from .routes import api_chat, api_chats, api_health, api_multimodal, api_settings, web

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

def _ensure_settings_columns() -> None:
    expected = {
        "default_image_model": "VARCHAR(255) DEFAULT 'bytedance-seed/seedream-4.5'",
        "default_video_analysis_model": "VARCHAR(255) DEFAULT 'google/gemini-2.5-pro'",
        "default_video_generation_model": "VARCHAR(255) DEFAULT ''",
        "request_timeout_seconds": "INTEGER DEFAULT 25",
        "max_video_upload_mb": "INTEGER DEFAULT 20",
        "persist_multimodal_history": "BOOLEAN DEFAULT 1",
    }
    with engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(settings)")).fetchall()
        names = {c[1] for c in columns}
        for name, ddl in expected.items():
            if name not in names:
                conn.execute(text(f"ALTER TABLE settings ADD COLUMN {name} {ddl}"))

_ensure_settings_columns()

app = FastAPI(title=config.app_name)
app.mount("/static", StaticFiles(directory="llm/app/static"), name="static")
app.mount("/generated-images", StaticFiles(directory=str(config.generated_images_dir)), name="generated-images")
app.mount("/input-images", StaticFiles(directory=str(config.input_images_dir)), name="input-images")

app.include_router(web.router)
app.include_router(api_health.router)
app.include_router(api_chats.router)
app.include_router(api_chat.router)
app.include_router(api_settings.router)
app.include_router(api_multimodal.router)
