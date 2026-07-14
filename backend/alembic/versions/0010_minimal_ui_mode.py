"""Add the user-selectable interface mode.

Revision ID: 0010
Revises: 0009_google_health
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009_google_health"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("ui_mode", sa.String(length=20), nullable=False, server_default="classic"),
    )


def downgrade() -> None:
    op.drop_column("users", "ui_mode")
