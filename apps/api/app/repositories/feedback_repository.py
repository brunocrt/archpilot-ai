"""
Repository for feedback persistence.

This module stores feedback ratings and optional comments from users about
assistant messages.  Each message may have at most one feedback entry.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..domain import models


class FeedbackRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_feedback(self, message_id: UUID, rating: str, comment: Optional[str] = None) -> models.Feedback:
        feedback = models.Feedback(message_id=message_id, rating=rating, comment=comment)
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def get_feedback(self, message_id: UUID) -> Optional[models.Feedback]:
        return self.db.query(models.Feedback).filter(models.Feedback.message_id == message_id).first()