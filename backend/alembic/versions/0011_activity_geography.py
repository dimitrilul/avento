"""Store activity geography independently from weather.

Revision ID: 0011
Revises: 0010
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("geography_data", sa.JSON(), nullable=True))
    op.add_column(
        "activities",
        sa.Column("geography_status", sa.String(length=30), nullable=False, server_default="pending"),
    )
    op.add_column("activities", sa.Column("geography_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_activity_geography_status",
        "activities",
        "geography_status IN ('pending', 'available', 'unavailable', 'error')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_activity_geography_status", "activities", type_="check")
    op.drop_column("activities", "geography_updated_at")
    op.drop_column("activities", "geography_status")
    op.drop_column("activities", "geography_data")
