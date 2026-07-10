"""Add OAuth 2.1 support for remote MCP clients.

Revision ID: 0006_mcp_oauth
Revises: 0005_mcp_server
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_mcp_oauth"
down_revision = "0005_mcp_server"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_oauth_clients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=120), nullable=False),
        sa.Column("client_name", sa.String(length=120), nullable=False),
        sa.Column("redirect_uris", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mcp_oauth_clients_client_id", "mcp_oauth_clients", ["client_id"], unique=True)

    for table_name, token_name in (
        ("mcp_oauth_authorization_codes", "code_hash"),
        ("mcp_oauth_access_tokens", "token_hash"),
        ("mcp_oauth_refresh_tokens", "token_hash"),
    ):
        columns = [
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column(token_name, sa.String(length=64), nullable=False),
            sa.Column("client_pk", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
        ]
        if table_name == "mcp_oauth_authorization_codes":
            columns.extend(
                [
                    sa.Column("redirect_uri", sa.String(length=2048), nullable=False),
                    sa.Column("code_challenge", sa.String(length=128), nullable=False),
                    sa.Column("code_challenge_method", sa.String(length=16), nullable=False),
                    sa.Column("scopes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
                    sa.Column("resource", sa.String(length=2048), nullable=False),
                    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
                ]
            )
        else:
            columns.extend(
                [
                    sa.Column("scopes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
                    sa.Column("resource", sa.String(length=2048), nullable=False),
                    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
                ]
            )
            if table_name == "mcp_oauth_access_tokens":
                columns.append(sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))
        columns.append(sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
        op.create_table(
            table_name,
            *columns,
            sa.ForeignKeyConstraint(["client_pk"], ["mcp_oauth_clients.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(f"ix_{table_name}_{token_name}", table_name, [token_name], unique=True)
        op.create_index(f"ix_{table_name}_client_pk", table_name, ["client_pk"], unique=False)
        op.create_index(f"ix_{table_name}_user_id", table_name, ["user_id"], unique=False)
        op.create_index(f"ix_{table_name}_expires_at", table_name, ["expires_at"], unique=False)


def downgrade() -> None:
    for table_name, token_name in (
        ("mcp_oauth_refresh_tokens", "token_hash"),
        ("mcp_oauth_access_tokens", "token_hash"),
        ("mcp_oauth_authorization_codes", "code_hash"),
    ):
        op.drop_index(f"ix_{table_name}_expires_at", table_name=table_name)
        op.drop_index(f"ix_{table_name}_user_id", table_name=table_name)
        op.drop_index(f"ix_{table_name}_client_pk", table_name=table_name)
        op.drop_index(f"ix_{table_name}_{token_name}", table_name=table_name)
        op.drop_table(table_name)
    op.drop_index("ix_mcp_oauth_clients_client_id", table_name="mcp_oauth_clients")
    op.drop_table("mcp_oauth_clients")
