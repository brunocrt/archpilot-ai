"""
Repository for conversation and message persistence.

Provides methods to create conversations, add messages, retrieve
conversations and messages.  Conversations record sequences of user and
assistant messages.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_
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

    def add_retrieval_logs(
        self,
        message_id: UUID,
        entries: list[dict],
    ) -> List[models.RetrievalLog]:
        logs = [models.RetrievalLog(message_id=message_id, **entry) for entry in entries]
        self.db.add_all(logs)
        self.db.commit()
        for log in logs:
            self.db.refresh(log)
        return logs

    def get_message(self, message_id: UUID) -> Optional[models.Message]:
        return self.db.query(models.Message).filter(models.Message.id == message_id).first()

    def get_previous_user_message(self, message: models.Message) -> Optional[models.Message]:
        return (
            self.db.query(models.Message)
            .filter(
                and_(
                    models.Message.conversation_id == message.conversation_id,
                    models.Message.role == "user",
                    models.Message.created_at <= message.created_at,
                )
            )
            .order_by(models.Message.created_at.desc())
            .first()
        )

    def list_retrieval_logs(self, message_id: UUID) -> List[models.RetrievalLog]:
        return (
            self.db.query(models.RetrievalLog)
            .filter(models.RetrievalLog.message_id == message_id)
            .order_by(models.RetrievalLog.rank)
            .all()
        )

    def list_messages(self, conversation_id: UUID) -> List[models.Message]:
        return (
            self.db.query(models.Message)
            .filter(models.Message.conversation_id == conversation_id)
            .order_by(models.Message.created_at)
            .all()
        )
