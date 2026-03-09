"""End-to-end chat flow orchestration service."""
from sqlalchemy.orm import Session

from ..config import get_config
from ..models import Message
from .conversation_service import ConversationService
from .llm_service import ResilientLLMService
from .model_router import ModelRouter
from .prompt_service import PromptService
from .settings_service import SettingsService


class ChatService:
    def __init__(self, db: Session, llm_service: ResilientLLMService):
        self.db = db
        self.config = get_config()
        self.conv_service = ConversationService(db)
        self.settings_service = SettingsService(db)
        self.prompt_service = PromptService()
        self.router = ModelRouter()
        self.llm_service = llm_service

    def send_message(self, conversation_id: int, username: str, content: str) -> tuple[Message, Message]:
        if len(content) > self.config.max_message_chars:
            raise ValueError(f"Mensagem excede limite de {self.config.max_message_chars} caracteres")

        conversation = self.conv_service.get_conversation(conversation_id, username)
        if not conversation:
            raise ValueError("Conversa não encontrada")

        settings = self.settings_service.get()
        user_msg = self.conv_service.add_message(conversation_id, username, "user", content)

        history = [{"role": msg.role, "content": msg.content} for msg in conversation.messages]
        prompt_messages = self.prompt_service.build_messages(settings.system_prompt, history, content)

        model_candidates = self.router.candidates(settings.model_name)
        result = None
        for model in model_candidates:
            settings.model_name = model
            result = self.llm_service.generate(prompt_messages, settings)
            if result.status == "ok":
                break

        assistant_msg = self.conv_service.add_message(
            conversation_id,
            username,
            "assistant",
            result.content,
            model_used=result.model_used,
            status=result.status,
            error_message=result.error_message,
        )
        return user_msg, assistant_msg
