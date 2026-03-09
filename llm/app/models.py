"""SQLAlchemy models for settings, conversations and messages."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    openrouter_api_key: Mapped[str] = mapped_column(String(255), default="")
    model_name: Mapped[str] = mapped_column(String(255), default="openrouter/auto")
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    system_prompt: Mapped[str] = mapped_column(
        Text,
        default="Você é uma assistente útil, objetiva e confiável.",
    )
    assistant_name: Mapped[str] = mapped_column(String(120), default="Kai")
    http_referer: Mapped[str] = mapped_column(String(255), default="")
    x_title: Mapped[str] = mapped_column(String(255), default="")

    default_image_model: Mapped[str] = mapped_column(String(255), default="bytedance-seed/seedream-4.5")
    default_video_analysis_model: Mapped[str] = mapped_column(String(255), default="nvidia/nemotron-nano-12b-v2-vl:free")
    default_video_generation_model: Mapped[str] = mapped_column(String(255), default="")
    request_timeout_seconds: Mapped[int] = mapped_column(Integer, default=25)
    max_video_upload_mb: Mapped[int] = mapped_column(Integer, default=20)
    persist_multimodal_history: Mapped[bool] = mapped_column(default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), index=True, default="default")
    title: Mapped[str] = mapped_column(String(255), default="Novo chat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ok")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")


class MultimodalHistory(Base):
    __tablename__ = "multimodal_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), index=True, default="default")
    item_type: Mapped[str] = mapped_column(String(32))
    model_name: Mapped[str] = mapped_column(String(255), default="")
    prompt: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="ok")
    response_text: Mapped[str] = mapped_column(Text, default="")
    asset_url: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
