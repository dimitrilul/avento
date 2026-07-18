"""Store activity quality findings and statistics inclusion preference.

Revision ID: 0014_activity_quality
Revises: 0013_import_jobs
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_activity_quality"
down_revision = "0013_import_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("data_quality_flags", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("activities", sa.Column("metric_provenance", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("activities", sa.Column("include_in_statistics", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_activities_include_in_statistics", "activities", ["include_in_statistics"])


def downgrade() -> None:
    op.drop_index("ix_activities_include_in_statistics", table_name="activities")
    op.drop_column("activities", "include_in_statistics")
    op.drop_column("activities", "metric_provenance")
    op.drop_column("activities", "data_quality_flags")
