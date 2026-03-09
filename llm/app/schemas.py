"""Pydantic schemas for API boundaries."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    model_used: str | None
    status: str
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationOut(BaseModel):
    id: int
    username: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


class CreateConversationIn(BaseModel):
    title: str | None = None


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class ChatResponseOut(BaseModel):
    conversation: ConversationOut
    user_message: MessageOut
    assistant_message: MessageOut


class SettingsIn(BaseModel):
    openrouter_api_key: str = ""
    model_name: str = "openrouter/auto"
    default_image_model: str = "sourceful/riverflow-v2-fast"
    default_video_analysis_model: str = "google/gemini-2.5-pro"
    default_video_generation_model: str = ""
    temperature: float = Field(default=0.7, ge=0, le=2)
    system_prompt: str = Field(default="Você é uma assistente útil, objetiva e confiável.", min_length=1, max_length=6000)
    assistant_name: str = Field(default="Kai", min_length=1, max_length=120)
    http_referer: str = ""
    x_title: str = ""
    request_timeout_seconds: int = Field(default=25, ge=5, le=300)
    max_video_upload_mb: int = Field(default=20, ge=1, le=200)
    persist_multimodal_history: bool = True


class SettingsOut(SettingsIn):
    updated_at: datetime


class ModelInfo(BaseModel):
    id: str
    name: str
    input_modalities: list[str] = []
    output_modalities: list[str] = []
    is_free: bool = False
    supports_image_generation: bool = False
    supports_video_input: bool = False


class ModelCapabilitiesOut(BaseModel):
    models: list[ModelInfo]
    image_models: list[ModelInfo]
    image_models_free: list[ModelInfo]
    image_models_paid: list[ModelInfo]
    video_input_models: list[ModelInfo]
    video_generation_models: list[ModelInfo]
    default_image_model: str


class ImageGenerationIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    model: str = ""


class ImageGenerationOut(BaseModel):
    status: str
    model: str
    prompt: str
    image_url: str
    file_path: str
    mime_type: str
    size_bytes: int
    text: str = ""


class MultimodalHistoryOut(BaseModel):
    id: int
    username: str
    item_type: str
    model_name: str
    prompt: str
    status: str
    response_text: str
    asset_url: str
    metadata_json: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoAnalysisOut(BaseModel):
    status: str
    model: str
    prompt: str
    result: str
