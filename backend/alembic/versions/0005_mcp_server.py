"""Add the secure read-only MCP server tables.

Revision ID: 0005_mcp_server
Revises: 0004_activity_insights
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_mcp_server"
down_revision = "0004_activity_insights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_clients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=80), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("secret_hash", sa.String(length=512), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mcp_clients_client_id", "mcp_clients", ["client_id"], unique=True)
    op.create_index(
        "ix_mcp_clients_created_by_user_id", "mcp_clients", ["created_by_user_id"], unique=False
    )
    op.create_index("ix_mcp_clients_owner_user_id", "mcp_clients", ["owner_user_id"], unique=False)

    op.create_table(
        "mcp_access_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_pk", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_pk"], ["mcp_clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mcp_access_tokens_client_pk", "mcp_access_tokens", ["client_pk"], unique=False
    )
    op.create_index(
        "ix_mcp_access_tokens_expires_at", "mcp_access_tokens", ["expires_at"], unique=False
    )
    op.create_index(
        "ix_mcp_access_tokens_token_hash", "mcp_access_tokens", ["token_hash"], unique=True
    )

    op.create_table(
        "mcp_audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_pk", sa.String(length=36), nullable=True),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("request_id_hash", sa.String(length=64), nullable=True),
        sa.Column("method", sa.String(length=80), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=True),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("error_type", sa.String(length=48), nullable=True),
        sa.Column("jsonrpc_error_code", sa.Integer(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_pk"], ["mcp_clients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mcp_audit_logs_client_created", "mcp_audit_logs", ["client_pk", "created_at"], unique=False
    )
    op.create_index("ix_mcp_audit_logs_created_at", "mcp_audit_logs", ["created_at"], unique=False)
    op.create_index(
        "ix_mcp_audit_logs_owner_user_id", "mcp_audit_logs", ["owner_user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_mcp_audit_logs_owner_user_id", table_name="mcp_audit_logs")
    op.drop_index("ix_mcp_audit_logs_created_at", table_name="mcp_audit_logs")
    op.drop_index("ix_mcp_audit_logs_client_created", table_name="mcp_audit_logs")
    op.drop_table("mcp_audit_logs")

    op.drop_index("ix_mcp_access_tokens_token_hash", table_name="mcp_access_tokens")
    op.drop_index("ix_mcp_access_tokens_expires_at", table_name="mcp_access_tokens")
    op.drop_index("ix_mcp_access_tokens_client_pk", table_name="mcp_access_tokens")
    op.drop_table("mcp_access_tokens")

    op.drop_index("ix_mcp_clients_owner_user_id", table_name="mcp_clients")
    op.drop_index("ix_mcp_clients_created_by_user_id", table_name="mcp_clients")
    op.drop_index("ix_mcp_clients_client_id", table_name="mcp_clients")
    op.drop_table("mcp_clients")
