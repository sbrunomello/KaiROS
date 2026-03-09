from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_llm_service, get_username
from ..schemas import ChatMessageIn, ChatResponseOut
from ..services.chat_service import ChatService
from ..services.llm_service import ResilientLLMService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{conversation_id}/messages", response_model=ChatResponseOut)
def send_message(
    conversation_id: int,
    payload: ChatMessageIn,
    username: str = Depends(get_username),
    db: Session = Depends(get_db),
    llm_service: ResilientLLMService = Depends(get_llm_service),
):
    service = ChatService(db, llm_service)
    try:
        user_message, assistant_message = service.send_message(conversation_id, username, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    conversation = service.conv_service.get_conversation(conversation_id, username)
    return {
        "conversation": conversation,
        "user_message": user_message,
        "assistant_message": assistant_message,
    }
