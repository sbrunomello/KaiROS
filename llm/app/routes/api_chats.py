from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import ConversationDetailOut, ConversationOut, CreateConversationIn
from ..services.conversation_service import ConversationService

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("", response_model=list[ConversationOut])
def list_chats(db: Session = Depends(get_db)):
    return ConversationService(db).list_conversations()


@router.post("", response_model=ConversationOut)
def create_chat(payload: CreateConversationIn, db: Session = Depends(get_db)):
    return ConversationService(db).create_conversation(payload.title)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_chat(conversation_id: int, db: Session = Depends(get_db)):
    conversation = ConversationService(db).get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return conversation
