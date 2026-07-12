"""Add private gamification state.

Revision ID: 0007_gamification
Revises: 0006_mcp_oauth
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_gamification"
down_revision = "0006_mcp_oauth"
branch_labels = None
depends_on = None


def _common_indexes(table: str, user_index: str) -> None:
    op.create_index(user_index, table, ["user_id"])


def upgrade() -> None:
    op.create_table(
        "gamification_badge_unlocks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("badge_key", sa.String(length=80), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_activity_id", sa.String(length=36), nullable=True),
        sa.Column("reward_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_activity_id"], ["activities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "badge_key", name="uq_gam_badge_user_key"),
        sa.CheckConstraint("reward_xp >= 0 AND reward_xp <= 100000", name="ck_gam_badge_reward_xp"),
    )
    _common_indexes("gamification_badge_unlocks", "ix_gamification_badge_unlocks_user_id")
    op.create_index("ix_gam_badge_user_unlocked", "gamification_badge_unlocks", ["user_id", "unlocked_at"])

    op.create_table(
        "gamification_goals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("metric", sa.String(length=40), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("period", sa.String(length=20), nullable=False, server_default="custom"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reward_xp", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("metric IN ('distance_m', 'activity_count', 'elevation_gain_m', 'moving_time_s', 'training_load', 'active_weeks', 'places_visited', 'hydration_activity_count', 'hydration_ml', 'recovery_gap_count', 'intensity_variety', 'weather_activity_count', 'village_count', 'city_count', 'municipality_count', 'state_count', 'country_count', 'longest_ride_m', 'highest_elevation_m', 'best_average_speed_mps')", name="ck_gam_goal_metric"),
        sa.CheckConstraint("period IN ('week', 'month', 'year', 'custom', 'lifetime')", name="ck_gam_goal_period"),
        sa.CheckConstraint("status IN ('active', 'paused', 'completed', 'expired')", name="ck_gam_goal_status"),
        sa.CheckConstraint("target_value > 0 AND target_value <= 1000000000000", name="ck_gam_goal_target"),
        sa.CheckConstraint("reward_xp >= 0 AND reward_xp <= 100000", name="ck_gam_goal_reward_xp"),
        sa.CheckConstraint("deadline IS NULL OR starts_on IS NULL OR deadline >= starts_on", name="ck_gam_goal_dates"),
    )
    _common_indexes("gamification_goals", "ix_gamification_goals_user_id")
    op.create_index("ix_gam_goal_user_status", "gamification_goals", ["user_id", "status"])
    op.create_index("ix_gam_goal_user_deadline", "gamification_goals", ["user_id", "deadline"])

    op.create_table(
        "gamification_challenges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("metric", sa.String(length=40), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("reward_xp", sa.Integer(), nullable=False, server_default="150"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="suggested"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="user"),
        sa.Column("personalization_reason", sa.String(length=500), nullable=True),
        sa.Column("weather_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("safety_note", sa.String(length=500), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "template_key", name="uq_gam_challenge_user_template"),
        sa.CheckConstraint("metric IN ('distance_m', 'activity_count', 'elevation_gain_m', 'moving_time_s', 'training_load', 'active_weeks', 'places_visited', 'hydration_activity_count', 'hydration_ml', 'recovery_gap_count', 'intensity_variety', 'weather_activity_count', 'village_count', 'city_count', 'municipality_count', 'state_count', 'country_count', 'longest_ride_m', 'highest_elevation_m', 'best_average_speed_mps')", name="ck_gam_challenge_metric"),
        sa.CheckConstraint("status IN ('suggested', 'accepted', 'completed', 'declined', 'expired')", name="ck_gam_challenge_status"),
        sa.CheckConstraint("source IN ('local', 'ai', 'user')", name="ck_gam_challenge_source"),
        sa.CheckConstraint("target_value > 0 AND target_value <= 1000000000000", name="ck_gam_challenge_target"),
        sa.CheckConstraint("duration_days >= 1 AND duration_days <= 366", name="ck_gam_challenge_duration"),
        sa.CheckConstraint("reward_xp >= 0 AND reward_xp <= 100000", name="ck_gam_challenge_reward_xp"),
        sa.CheckConstraint("expires_on IS NULL OR starts_on IS NULL OR expires_on >= starts_on", name="ck_gam_challenge_dates"),
    )
    _common_indexes("gamification_challenges", "ix_gamification_challenges_user_id")
    op.create_index("ix_gam_challenge_user_status", "gamification_challenges", ["user_id", "status"])
    op.create_index("ix_gam_challenge_user_expiry", "gamification_challenges", ["user_id", "expires_on"])

    op.create_table(
        "gamification_discoveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("location_key", sa.String(length=96), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("region", sa.String(length=200), nullable=True),
        sa.Column("country_code", sa.String(length=3), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("first_discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_activity_id", sa.String(length=36), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["first_activity_id"], ["activities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "kind", "location_key", name="uq_gam_discovery_user_place"),
        sa.CheckConstraint("kind IN ('village', 'city', 'municipality', 'state', 'country')", name="ck_gam_discovery_kind"),
        sa.CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_gam_discovery_lat"),
        sa.CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="ck_gam_discovery_lon"),
    )
    _common_indexes("gamification_discoveries", "ix_gamification_discoveries_user_id")
    op.create_index("ix_gam_discovery_user_kind", "gamification_discoveries", ["user_id", "kind"])
    op.create_index("ix_gam_discovery_user_first", "gamification_discoveries", ["user_id", "first_discovered_at"])

    op.create_table(
        "gamification_activity_discoveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("activity_id", sa.String(length=36), nullable=False),
        sa.Column("discovery_id", sa.String(length=36), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["discovery_id"], ["gamification_discoveries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id", "discovery_id", name="uq_gam_activity_discovery"),
    )
    _common_indexes("gamification_activity_discoveries", "ix_gamification_activity_discoveries_user_id")
    op.create_index("ix_gam_actdisc_user_activity", "gamification_activity_discoveries", ["user_id", "activity_id"])
    op.create_index("ix_gam_actdisc_user_discovery", "gamification_activity_discoveries", ["user_id", "discovery_id"])

    op.create_table(
        "gamification_yearly_awards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("award_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("tier", sa.String(length=20), nullable=False, server_default="personal"),
        sa.Column("icon", sa.String(length=80), nullable=True),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reward_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "year", "award_key", name="uq_gam_award_user_year_key"),
        sa.CheckConstraint("year >= 1900 AND year <= 9999", name="ck_gam_award_year"),
        sa.CheckConstraint("value IS NULL OR value >= 0", name="ck_gam_award_value"),
        sa.CheckConstraint("reward_xp >= 0 AND reward_xp <= 100000", name="ck_gam_award_reward_xp"),
    )
    _common_indexes("gamification_yearly_awards", "ix_gamification_yearly_awards_user_id")
    op.create_index("ix_gam_award_user_year", "gamification_yearly_awards", ["user_id", "year"])


def downgrade() -> None:
    for index, table in (
        ("ix_gam_award_user_year", "gamification_yearly_awards"),
        ("ix_gamification_yearly_awards_user_id", "gamification_yearly_awards"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_table("gamification_yearly_awards")
    for index, table in (
        ("ix_gam_actdisc_user_discovery", "gamification_activity_discoveries"),
        ("ix_gam_actdisc_user_activity", "gamification_activity_discoveries"),
        ("ix_gamification_activity_discoveries_user_id", "gamification_activity_discoveries"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_table("gamification_activity_discoveries")
    for index, table in (
        ("ix_gam_discovery_user_first", "gamification_discoveries"),
        ("ix_gam_discovery_user_kind", "gamification_discoveries"),
        ("ix_gamification_discoveries_user_id", "gamification_discoveries"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_table("gamification_discoveries")
    for index, table in (
        ("ix_gam_challenge_user_expiry", "gamification_challenges"),
        ("ix_gam_challenge_user_status", "gamification_challenges"),
        ("ix_gamification_challenges_user_id", "gamification_challenges"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_table("gamification_challenges")
    for index, table in (
        ("ix_gam_goal_user_deadline", "gamification_goals"),
        ("ix_gam_goal_user_status", "gamification_goals"),
        ("ix_gamification_goals_user_id", "gamification_goals"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_table("gamification_goals")
    for index, table in (
        ("ix_gam_badge_user_unlocked", "gamification_badge_unlocks"),
        ("ix_gamification_badge_unlocks_user_id", "gamification_badge_unlocks"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_table("gamification_badge_unlocks")
