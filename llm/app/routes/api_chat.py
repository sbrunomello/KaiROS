from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_llm_service
from ..schemas import ChatMessageIn, ChatResponseOut
from ..services.chat_service import ChatService
from ..services.llm_service import ResilientLLMService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{conversation_id}/messages", response_model=ChatResponseOut)
def send_message(
    conversation_id: int,
    payload: ChatMessageIn,
    db: Session = Depends(get_db),
    llm_service: ResilientLLMService = Depends(get_llm_service),
):
    service = ChatService(db, llm_service)
    try:
        user_message, assistant_message = service.send_message(conversation_id, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    conversation = service.conv_service.get_conversation(conversation_id)
    return {
        "conversation": conversation,
        "user_message": user_message,
        "assistant_message": assistant_message,
    }
