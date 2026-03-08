"""Read/write runtime settings persisted in SQLite."""
from sqlalchemy.orm import Session

from ..models import Settings
from ..schemas import SettingsIn


class SettingsService:
    def __init__(self, db: Session):
        self.db = db

    def get(self) -> Settings:
        settings = self.db.get(Settings, 1)
        if not settings:
            settings = Settings(id=1)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update(self, payload: SettingsIn) -> Settings:
        settings = self.get()
        for field, value in payload.model_dump().items():
            setattr(settings, field, value)
        self.db.commit()
        self.db.refresh(settings)
        return settings
