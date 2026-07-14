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
    with op.batch_alter_table("activities") as batch_op:
        batch_op.add_column(sa.Column("geography_data", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("geography_status", sa.String(length=30), nullable=False, server_default="pending")
        )
        batch_op.add_column(sa.Column("geography_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_check_constraint(
            "ck_activity_geography_status",
            "geography_status IN ('pending', 'available', 'unavailable', 'error')",
        )


def downgrade() -> None:
    with op.batch_alter_table("activities") as batch_op:
        batch_op.drop_constraint("ck_activity_geography_status", type_="check")
        batch_op.drop_column("geography_updated_at")
        batch_op.drop_column("geography_status")
        batch_op.drop_column("geography_data")
