"""preserve the retired Google Health migration revision

Revision ID: 0009_google_health
Revises: 0008_authentication_factors

The Google Health integration was removed after some installations had already
recorded this revision. Keeping the revision as a no-op lets those databases
continue through normal Alembic startup without recreating or deleting data.
"""


revision = "0009_google_health"
down_revision = "0008_authentication_factors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
