"""
Feedback API.

Allows users to submit ratings and comments on assistant messages.  Each
message can have at most one feedback entry.  If feedback for a message
already exists, it will be overwritten.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_db_session
from ..domain import schemas
from ..repositories.feedback_repository import FeedbackRepository


router = APIRouter()


@router.post("/", response_model=schemas.FeedbackResponse)
def create_feedback(payload: schemas.FeedbackCreate, db=Depends(get_db_session)) -> schemas.FeedbackResponse:
    """Create or update feedback for a message."""
    repo = FeedbackRepository(db)
    # Check if feedback already exists for the message and delete it
    existing = repo.get_feedback(payload.message_id)
    if existing:
        db.delete(existing)
        db.commit()
    feedback = repo.create_feedback(
        message_id=payload.message_id, rating=payload.rating, comment=payload.comment
    )
    return schemas.FeedbackResponse(
        id=str(feedback.id),
        message_id=str(feedback.message_id),
        rating=feedback.rating,
        comment=feedback.comment,
        created_at=feedback.created_at,
    )