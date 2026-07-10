"""Add coaching profile fields and avatar metadata.

Revision ID: 0003
Revises: 0002
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("training_goals", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("users", sa.Column("avatar_path", sa.String(length=1024), nullable=True))
    op.add_column("users", sa.Column("avatar_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_updated_at")
    op.drop_column("users", "avatar_path")
    op.drop_column("users", "training_goals")
