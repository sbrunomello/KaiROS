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

    # Provider-agnostic fields (OpenRouter fields remain as legacy/deprecated)
    groq_api_key: Mapped[str] = mapped_column(String(255), default="")
    huggingface_api_key: Mapped[str] = mapped_column(String(255), default="")
    cloudflare_api_token: Mapped[str] = mapped_column(String(255), default="")
    cloudflare_account_id: Mapped[str] = mapped_column(String(128), default="")
    together_api_key: Mapped[str] = mapped_column(String(255), default="")
    deepinfra_api_key: Mapped[str] = mapped_column(String(255), default="")
    chat_provider: Mapped[str] = mapped_column(String(32), default="groq")
    chat_fallback_provider: Mapped[str] = mapped_column(String(32), default="openrouter")
    chat_model_name: Mapped[str] = mapped_column(String(255), default="openrouter/auto")
    speech_provider: Mapped[str] = mapped_column(String(32), default="groq")
    speech_model_name: Mapped[str] = mapped_column(String(255), default="whisper-large-v3-turbo")
    whisper_cpp_binary_path: Mapped[str] = mapped_column(String(255), default="")
    whisper_cpp_model_path: Mapped[str] = mapped_column(String(255), default="")
    vision_provider: Mapped[str] = mapped_column(String(32), default="groq")
    vision_fallback_provider: Mapped[str] = mapped_column(String(32), default="")
    vision_model_name: Mapped[str] = mapped_column(String(255), default="llama-3.2-11b-vision-preview")
    image_gen_provider: Mapped[str] = mapped_column(String(32), default="openrouter")
    image_gen_fallback_provider: Mapped[str] = mapped_column(String(32), default="")
    image_edit_provider: Mapped[str] = mapped_column(String(32), default="openrouter")
    image_edit_fallback_provider: Mapped[str] = mapped_column(String(32), default="")
    image_edit_enabled: Mapped[bool] = mapped_column(default=False)
    image_edit_model_name: Mapped[str] = mapped_column(String(255), default="")
    video_analysis_mode: Mapped[str] = mapped_column(String(32), default="legacy")
    video_enable_vision: Mapped[bool] = mapped_column(default=False)
    video_frame_sample_seconds: Mapped[int] = mapped_column(Integer, default=5)
    ffmpeg_binary_path: Mapped[str] = mapped_column(String(255), default="ffmpeg")
    openrouter_default_image_model: Mapped[str] = mapped_column(String(255), default="bytedance-seed/seedream-4.5")
    hf_default_image_model: Mapped[str] = mapped_column(String(255), default="black-forest-labs/FLUX.1-schnell")
    cloudflare_default_chat_model: Mapped[str] = mapped_column(String(255), default="@cf/meta/llama-3.1-8b-instruct")
    cloudflare_default_vision_model: Mapped[str] = mapped_column(String(255), default="@cf/llava-hf/llava-1.5-7b-hf")
    cloudflare_default_image_model: Mapped[str] = mapped_column(String(255), default="@cf/stabilityai/stable-diffusion-xl-base-1.0")
    together_default_chat_model: Mapped[str] = mapped_column(String(255), default="meta-llama/Llama-3.1-8B-Instruct-Turbo")
    together_default_vision_model: Mapped[str] = mapped_column(String(255), default="meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo")
    together_default_image_model: Mapped[str] = mapped_column(String(255), default="black-forest-labs/FLUX.1-schnell")
    deepinfra_default_chat_model: Mapped[str] = mapped_column(String(255), default="meta-llama/Meta-Llama-3.1-8B-Instruct")
    deepinfra_default_vision_model: Mapped[str] = mapped_column(String(255), default="meta-llama/Llama-3.2-11B-Vision-Instruct")
    deepinfra_default_image_model: Mapped[str] = mapped_column(String(255), default="black-forest-labs/FLUX.1-schnell")
    hf_image_edit_endpoint: Mapped[str] = mapped_column(String(512), default="")
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
