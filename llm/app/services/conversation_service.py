"""Conversation and message persistence helpers."""
from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from ..models import Conversation, Message


class ConversationService:
    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, username: str, title: str | None = None) -> Conversation:
        conversation = Conversation(username=username, title=title or "Novo chat")
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_conversations(self, username: str) -> list[Conversation]:
        return (
            self.db.query(Conversation)
            .filter(Conversation.username == username)
            .order_by(desc(Conversation.updated_at))
            .all()
        )

    def get_conversation(self, conversation_id: int, username: str) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .options(joinedload(Conversation.messages))
            .filter(Conversation.id == conversation_id, Conversation.username == username)
            .first()
        )

    def add_message(
        self,
        conversation_id: int,
        username: str,
        role: str,
        content: str,
        model_used: str | None = None,
        status: str = "ok",
        error_message: str | None = None,
    ) -> Message:
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.username == username,
        ).first()
        if not conversation:
            raise ValueError("Conversa não encontrada para este usuário")

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_used=model_used,
            status=status,
            error_message=error_message,
        )
        self.db.add(message)
        if conversation.title == "Novo chat" and role == "user":
            conversation.title = content[:60].strip() or "Novo chat"
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(message)
        return message
