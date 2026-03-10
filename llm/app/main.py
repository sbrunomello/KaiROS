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
        "default_video_analysis_model": "VARCHAR(255) DEFAULT 'nvidia/nemotron-nano-12b-v2-vl:free'",
        "default_video_generation_model": "VARCHAR(255) DEFAULT ''",
        "request_timeout_seconds": "INTEGER DEFAULT 25",
        "max_video_upload_mb": "INTEGER DEFAULT 20",
        "persist_multimodal_history": "BOOLEAN DEFAULT 1",
        "groq_api_key": "VARCHAR(255) DEFAULT ''",
        "huggingface_api_key": "VARCHAR(255) DEFAULT ''",
        "cloudflare_api_token": "VARCHAR(255) DEFAULT ''",
        "cloudflare_account_id": "VARCHAR(128) DEFAULT ''",
        "together_api_key": "VARCHAR(255) DEFAULT ''",
        "deepinfra_api_key": "VARCHAR(255) DEFAULT ''",
        "chat_provider": "VARCHAR(32) DEFAULT 'groq'",
        "chat_fallback_provider": "VARCHAR(32) DEFAULT 'openrouter'",
        "chat_model_name": "VARCHAR(255) DEFAULT 'openrouter/auto'",
        "speech_provider": "VARCHAR(32) DEFAULT 'groq'",
        "speech_model_name": "VARCHAR(255) DEFAULT 'whisper-large-v3-turbo'",
        "whisper_cpp_binary_path": "VARCHAR(255) DEFAULT ''",
        "whisper_cpp_model_path": "VARCHAR(255) DEFAULT ''",
        "vision_provider": "VARCHAR(32) DEFAULT 'groq'",
        "vision_fallback_provider": "VARCHAR(32) DEFAULT ''",
        "vision_model_name": "VARCHAR(255) DEFAULT 'llama-3.2-11b-vision-preview'",
        "image_gen_provider": "VARCHAR(32) DEFAULT 'openrouter'",
        "image_gen_fallback_provider": "VARCHAR(32) DEFAULT ''",
        "image_edit_provider": "VARCHAR(32) DEFAULT 'openrouter'",
        "image_edit_fallback_provider": "VARCHAR(32) DEFAULT ''",
        "image_edit_enabled": "BOOLEAN DEFAULT 0",
        "image_edit_model_name": "VARCHAR(255) DEFAULT ''",
        "video_analysis_mode": "VARCHAR(32) DEFAULT 'legacy'",
        "video_enable_vision": "BOOLEAN DEFAULT 0",
        "video_frame_sample_seconds": "INTEGER DEFAULT 5",
        "ffmpeg_binary_path": "VARCHAR(255) DEFAULT 'ffmpeg'",
        "openrouter_default_image_model": "VARCHAR(255) DEFAULT 'bytedance-seed/seedream-4.5'",
        "hf_default_image_model": "VARCHAR(255) DEFAULT 'black-forest-labs/FLUX.1-schnell'",
        "cloudflare_default_chat_model": "VARCHAR(255) DEFAULT '@cf/meta/llama-3.1-8b-instruct'",
        "cloudflare_default_vision_model": "VARCHAR(255) DEFAULT '@cf/llava-hf/llava-1.5-7b-hf'",
        "cloudflare_default_image_model": "VARCHAR(255) DEFAULT '@cf/stabilityai/stable-diffusion-xl-base-1.0'",
        "together_default_chat_model": "VARCHAR(255) DEFAULT 'meta-llama/Llama-3.1-8B-Instruct-Turbo'",
        "together_default_vision_model": "VARCHAR(255) DEFAULT 'meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo'",
        "together_default_image_model": "VARCHAR(255) DEFAULT 'black-forest-labs/FLUX.1-schnell'",
        "deepinfra_default_chat_model": "VARCHAR(255) DEFAULT 'meta-llama/Meta-Llama-3.1-8B-Instruct'",
        "deepinfra_default_vision_model": "VARCHAR(255) DEFAULT 'meta-llama/Llama-3.2-11B-Vision-Instruct'",
        "deepinfra_default_image_model": "VARCHAR(255) DEFAULT 'black-forest-labs/FLUX.1-schnell'",
        "hf_image_edit_endpoint": "VARCHAR(512) DEFAULT ''",
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
app.mount("/input-videos", StaticFiles(directory=str(config.input_videos_dir)), name="input-videos")

app.include_router(web.router)
app.include_router(api_health.router)
app.include_router(api_chats.router)
app.include_router(api_chat.router)
app.include_router(api_settings.router)
app.include_router(api_multimodal.router)
