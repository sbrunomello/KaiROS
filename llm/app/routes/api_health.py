from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.settings_service import SettingsService

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@router.get("/status")
def status(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    settings = SettingsService(db).get()
    return {
        "db": "ok",
        "settings_loaded": True,
        "model_configured": settings.model_name,
    }
