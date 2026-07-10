"""Add hydration, AI transparency, and activity photos.

Revision ID: 0004_activity_insights
Revises: 0003
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_activity_insights"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("hydration_ml", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("ai_data_basis", sa.JSON(), nullable=True))

    op.create_table(
        "activity_photos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("activity_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("caption", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("size_bytes > 0", name="ck_activity_photo_size_positive"),
        sa.CheckConstraint("width > 0 AND height > 0", name="ck_activity_photo_dimensions_positive"),
        sa.CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_activity_photo_latitude"),
        sa.CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_activity_photo_longitude",
        ),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id", "file_hash", name="uq_activity_photo_hash"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index("ix_activity_photos_activity_id", "activity_photos", ["activity_id"], unique=False)
    op.create_index("ix_activity_photos_file_hash", "activity_photos", ["file_hash"], unique=False)
    op.create_index("ix_activity_photos_user_id", "activity_photos", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activity_photos_user_id", table_name="activity_photos")
    op.drop_index("ix_activity_photos_file_hash", table_name="activity_photos")
    op.drop_index("ix_activity_photos_activity_id", table_name="activity_photos")
    op.drop_table("activity_photos")
    op.drop_column("activities", "ai_data_basis")
    op.drop_column("activities", "hydration_ml")
