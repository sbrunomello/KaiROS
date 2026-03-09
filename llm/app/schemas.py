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
    temperature: float = Field(default=0.7, ge=0, le=2)
    system_prompt: str = Field(default="Você é uma assistente útil, objetiva e confiável.", min_length=1, max_length=6000)
    assistant_name: str = Field(default="Kai", min_length=1, max_length=120)
    http_referer: str = ""
    x_title: str = ""


class SettingsOut(SettingsIn):
    updated_at: datetime
