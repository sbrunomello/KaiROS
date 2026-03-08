from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import SettingsIn, SettingsOut
from ..services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return SettingsService(db).get()


@router.put("", response_model=SettingsOut)
def update_settings(payload: SettingsIn, db: Session = Depends(get_db)):
    return SettingsService(db).update(payload)
