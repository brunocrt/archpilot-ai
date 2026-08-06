"""add retrieval diagnostics fields

Revision ID: 0002_retrieval_diagnostics
Revises: 0001_baseline_schema
Create Date: 2026-08-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_retrieval_diagnostics"
down_revision: Union[str, None] = "0001_baseline_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("retrieval_logs", sa.Column("retrieval_signal", sa.String(), nullable=True))
    op.add_column("retrieval_logs", sa.Column("rank", sa.Integer(), nullable=True))
    op.add_column("retrieval_logs", sa.Column("retrieval_latency_ms", sa.Float(), nullable=True))
    op.add_column("retrieval_logs", sa.Column("applied_filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("retrieval_logs", sa.Column("retrieval_mode", sa.String(), nullable=True))
    op.add_column("retrieval_logs", sa.Column("embedding_model", sa.String(), nullable=True))
    op.add_column("retrieval_logs", sa.Column("llm_provider", sa.String(), nullable=True))
    op.add_column("retrieval_logs", sa.Column("llm_model", sa.String(), nullable=True))
    op.add_column("retrieval_logs", sa.Column("created_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("retrieval_logs", "created_at")
    op.drop_column("retrieval_logs", "llm_model")
    op.drop_column("retrieval_logs", "llm_provider")
    op.drop_column("retrieval_logs", "embedding_model")
    op.drop_column("retrieval_logs", "retrieval_mode")
    op.drop_column("retrieval_logs", "applied_filters")
    op.drop_column("retrieval_logs", "retrieval_latency_ms")
    op.drop_column("retrieval_logs", "rank")
    op.drop_column("retrieval_logs", "retrieval_signal")
