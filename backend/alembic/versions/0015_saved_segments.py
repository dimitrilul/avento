"""Persist user-selected route segments.

Revision ID: 0015_saved_segments
Revises: 0014_activity_quality
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_saved_segments"
down_revision = "0014_activity_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_segments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_id", sa.String(length=36), sa.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("start_m", sa.Float(), nullable=False),
        sa.Column("end_m", sa.Float(), nullable=False),
        sa.Column("route_signature", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_saved_segments_user_id", "saved_segments", ["user_id"])
    op.create_index("ix_saved_segments_activity_id", "saved_segments", ["activity_id"])


def downgrade() -> None:
    op.drop_table("saved_segments")
