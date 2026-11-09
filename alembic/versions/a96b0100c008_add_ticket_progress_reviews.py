"""add ticket progress reviews

Revision ID: a96b0100c008
Revises: a95b0100c007
"""
from alembic import op
import sqlalchemy as sa

revision = "a96b0100c008"
down_revision = "a95b0100c007"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("ai_reviews", sa.Column("review_kind", sa.String(50), nullable=False, server_default="ticket_review"))
    op.add_column("ai_reviews", sa.Column("source_evidence", sa.JSON(), nullable=True))
    op.add_column("ai_reviews", sa.Column("progress_suggestions", sa.JSON(), nullable=True))
    op.add_column("ai_reviews", sa.Column("applied_progress", sa.JSON(), nullable=True))

def downgrade():
    op.drop_column("ai_reviews", "applied_progress")
    op.drop_column("ai_reviews", "progress_suggestions")
    op.drop_column("ai_reviews", "source_evidence")
    op.drop_column("ai_reviews", "review_kind")
