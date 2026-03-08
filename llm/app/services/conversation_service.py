"""Conversation and message persistence helpers."""
from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from ..models import Conversation, Message


class ConversationService:
    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, title: str | None = None) -> Conversation:
        conversation = Conversation(title=title or "Novo chat")
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_conversations(self) -> list[Conversation]:
        return self.db.query(Conversation).order_by(desc(Conversation.updated_at)).all()

    def get_conversation(self, conversation_id: int) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .options(joinedload(Conversation.messages))
            .filter(Conversation.id == conversation_id)
            .first()
        )

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model_used: str | None = None,
        status: str = "ok",
        error_message: str | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_used=model_used,
            status=status,
            error_message=error_message,
        )
        self.db.add(message)
        conversation = self.db.get(Conversation, conversation_id)
        if conversation:
            if conversation.title == "Novo chat" and role == "user":
                conversation.title = content[:60].strip() or "Novo chat"
            conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(message)
        return message
