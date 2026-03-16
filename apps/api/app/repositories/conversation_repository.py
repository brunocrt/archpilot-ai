"""
Repository for conversation and message persistence.

Provides methods to create conversations, add messages, retrieve
conversations and messages.  Conversations record sequences of user and
assistant messages.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..domain import models


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_conversation(self, title: Optional[str] = None) -> models.Conversation:
        conversation = models.Conversation(title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation(self, conversation_id: UUID) -> Optional[models.Conversation]:
        return self.db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()

    def list_conversations(self) -> List[models.Conversation]:
        return self.db.query(models.Conversation).order_by(models.Conversation.created_at.desc()).all()

    def add_message(self, conversation_id: UUID, role: str, content: str) -> models.Message:
        message = models.Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_messages(self, conversation_id: UUID) -> List[models.Message]:
        return (
            self.db.query(models.Message)
            .filter(models.Message.conversation_id == conversation_id)
            .order_by(models.Message.created_at)
            .all()
        )