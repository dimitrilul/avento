"""Keep immutable originals and process optimized photo variants asynchronously.

Revision ID: 0012_activity_photo_originals
Revises: 0011_activity_geography
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_activity_photo_originals"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activity_photos", sa.Column("original_storage_path", sa.String(length=1024), nullable=True))
    op.add_column("activity_photos", sa.Column("original_content_type", sa.String(length=100), nullable=True))
    op.add_column("activity_photos", sa.Column("original_size_bytes", sa.Integer(), nullable=True))
    op.add_column("activity_photos", sa.Column("processing_status", sa.String(length=20), nullable=True))
    op.execute(
        sa.text(
            "UPDATE activity_photos SET original_storage_path = storage_path, "
            "original_content_type = content_type, original_size_bytes = size_bytes, "
            "processing_status = 'ready'"
        )
    )
    with op.batch_alter_table("activity_photos") as batch:
        batch.alter_column("original_storage_path", nullable=False)
        batch.alter_column("original_content_type", nullable=False)
        batch.alter_column("original_size_bytes", nullable=False)
        batch.alter_column("processing_status", nullable=False, server_default="pending")
        batch.create_unique_constraint("uq_activity_photo_original_storage_path", ["original_storage_path"])
        batch.alter_column("storage_path", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("activity_photos") as batch:
        batch.alter_column("storage_path", nullable=False)
        batch.drop_constraint("uq_activity_photo_original_storage_path", type_="unique")
        batch.drop_column("processing_status")
        batch.drop_column("original_size_bytes")
        batch.drop_column("original_content_type")
        batch.drop_column("original_storage_path")
