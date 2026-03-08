"""Standalone FastAPI app entrypoint for llm chat subproject."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_config
from .db import Base, engine
from .logging_conf import setup_logging
from .routes import api_chat, api_chats, api_health, api_settings, web

config = get_config()
setup_logging(config.debug)
Base.metadata.create_all(bind=engine)

app = FastAPI(title=config.app_name)
app.mount("/static", StaticFiles(directory="llm/app/static"), name="static")

app.include_router(web.router)
app.include_router(api_health.router)
app.include_router(api_chats.router)
app.include_router(api_chat.router)
app.include_router(api_settings.router)
