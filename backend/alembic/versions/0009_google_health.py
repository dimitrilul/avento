"""add cloud Google Health API v4 integration

Revision ID: 0009_google_health
Revises: 0008_authentication_factors
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_google_health"
down_revision = "0008_authentication_factors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "health_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("health_user_id_hash", sa.String(64), nullable=False),
        sa.Column("health_user_id_encrypted", sa.Text(), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("granted_scopes", sa.JSON(), nullable=False),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_health_connection_user"),
        sa.UniqueConstraint("health_user_id_hash", name="uq_health_connection_external_user"),
        sa.CheckConstraint(
            "status IN ('connected', 'reauthorization_required', 'revoked', 'error')",
            name="ck_health_connection_status",
        ),
    )
    op.create_index("ix_health_connections_user_id", "health_connections", ["user_id"])
    op.create_index("ix_health_connections_access_token_expires_at", "health_connections", ["access_token_expires_at"])

    op.create_table(
        "health_oauth_states",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("pkce_verifier_encrypted", sa.Text(), nullable=False),
        sa.Column("redirect_uri", sa.String(2048), nullable=False),
        sa.Column("requested_scopes", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("state_hash", name="uq_health_oauth_state_hash"),
    )
    op.create_index("ix_health_oauth_states_user_id", "health_oauth_states", ["user_id"])
    op.create_index("ix_health_oauth_states_state_hash", "health_oauth_states", ["state_hash"])
    op.create_index("ix_health_oauth_states_expires_at", "health_oauth_states", ["expires_at"])

    op.create_table(
        "health_data_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("health_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("recording_method", sa.String(40), nullable=True),
        sa.Column("platform", sa.String(40), nullable=True),
        sa.Column("device_manufacturer", sa.String(120), nullable=True),
        sa.Column("device_name", sa.String(160), nullable=True),
        sa.Column("device_form_factor", sa.String(60), nullable=True),
        sa.Column("application_name", sa.String(160), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connection_id", "fingerprint", name="uq_health_source_fingerprint"),
    )
    op.create_index("ix_health_data_sources_connection_id", "health_data_sources", ["connection_id"])

    op.create_table(
        "health_sync_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("health_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("range_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("range_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("stored_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('running', 'succeeded', 'partial', 'failed')", name="ck_health_sync_run_status"),
        sa.CheckConstraint("fetched_count >= 0 AND stored_count >= 0 AND rejected_count >= 0", name="ck_health_sync_counts"),
    )
    op.create_index("ix_health_sync_runs_connection_id", "health_sync_runs", ["connection_id"])
    op.create_index("ix_health_sync_runs_user_id", "health_sync_runs", ["user_id"])
    op.create_index("ix_health_sync_run_user_started", "health_sync_runs", ["user_id", "started_at"])

    op.create_table(
        "health_sync_cursors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("health_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_type", sa.String(80), nullable=False),
        sa.Column("completed_through", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(80), nullable=True),
        sa.UniqueConstraint("connection_id", "data_type", name="uq_health_sync_cursor_type"),
    )
    op.create_index("ix_health_sync_cursors_connection_id", "health_sync_cursors", ["connection_id"])

    op.create_table(
        "health_metrics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("health_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("health_data_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("data_type", sa.String(80), nullable=False),
        sa.Column("metric_type", sa.String(100), nullable=False),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("local_date", sa.Date(), nullable=True),
        sa.Column("utc_offset_seconds", sa.Integer(), nullable=True),
        sa.Column("source_family", sa.String(40), nullable=False),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connection_id", "dedupe_hash", name="uq_health_metric_dedupe"),
        sa.CheckConstraint("value = value", name="ck_health_metric_finite"),
    )
    op.create_index("ix_health_metrics_connection_id", "health_metrics", ["connection_id"])
    op.create_index("ix_health_metrics_user_id", "health_metrics", ["user_id"])
    op.create_index("ix_health_metrics_source_id", "health_metrics", ["source_id"])
    op.create_index("ix_health_metric_user_date_type", "health_metrics", ["user_id", "local_date", "metric_type"])

    op.create_table(
        "health_sleep_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("health_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("health_data_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_utc_offset_seconds", sa.Integer(), nullable=False),
        sa.Column("end_utc_offset_seconds", sa.Integer(), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("sleep_type", sa.String(30), nullable=False),
        sa.Column("is_nap", sa.Boolean(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("manually_edited", sa.Boolean(), nullable=False),
        sa.Column("stages_status", sa.String(60), nullable=True),
        sa.Column("minutes_asleep", sa.Integer(), nullable=True),
        sa.Column("minutes_awake", sa.Integer(), nullable=True),
        sa.Column("minutes_to_fall_asleep", sa.Integer(), nullable=True),
        sa.Column("overlaps_other_session", sa.Boolean(), nullable=False),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connection_id", "dedupe_hash", name="uq_health_sleep_dedupe"),
        sa.CheckConstraint("end_at > start_at", name="ck_health_sleep_interval"),
    )
    op.create_index("ix_health_sleep_sessions_connection_id", "health_sleep_sessions", ["connection_id"])
    op.create_index("ix_health_sleep_sessions_user_id", "health_sleep_sessions", ["user_id"])
    op.create_index("ix_health_sleep_user_end", "health_sleep_sessions", ["user_id", "end_at"])

    op.create_table(
        "health_sleep_stages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("health_sleep_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_utc_offset_seconds", sa.Integer(), nullable=False),
        sa.Column("end_utc_offset_seconds", sa.Integer(), nullable=False),
        sa.Column("stage_type", sa.String(30), nullable=False),
        sa.UniqueConstraint("session_id", "start_at", "end_at", "stage_type", name="uq_health_sleep_stage"),
        sa.CheckConstraint("end_at > start_at", name="ck_health_sleep_stage_interval"),
    )
    op.create_index("ix_health_sleep_stages_session_id", "health_sleep_stages", ["session_id"])

    op.create_table(
        "health_exercises",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("health_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("health_data_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_utc_offset_seconds", sa.Integer(), nullable=False),
        sa.Column("end_utc_offset_seconds", sa.Integer(), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("exercise_type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("active_duration_seconds", sa.Float(), nullable=True),
        sa.Column("calories_kcal", sa.Float(), nullable=True),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("average_heart_rate_bpm", sa.Integer(), nullable=True),
        sa.Column("active_zone_minutes", sa.Integer(), nullable=True),
        sa.Column("heart_rate_zone_seconds", sa.JSON(), nullable=False),
        sa.Column("has_gps", sa.Boolean(), nullable=False),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connection_id", "dedupe_hash", name="uq_health_exercise_dedupe"),
        sa.CheckConstraint("end_at > start_at", name="ck_health_exercise_interval"),
    )
    op.create_index("ix_health_exercises_connection_id", "health_exercises", ["connection_id"])
    op.create_index("ix_health_exercises_user_id", "health_exercises", ["user_id"])
    op.create_index("ix_health_exercise_user_start", "health_exercises", ["user_id", "start_at"])

    op.create_table(
        "health_heart_rate_aggregates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("health_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("granularity", sa.String(20), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=True),
        sa.Column("min_bpm", sa.Float(), nullable=False),
        sa.Column("avg_bpm", sa.Float(), nullable=False),
        sa.Column("max_bpm", sa.Float(), nullable=False),
        sa.Column("sleep_session_id", sa.String(36), sa.ForeignKey("health_sleep_sessions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("exercise_id", sa.String(36), sa.ForeignKey("health_exercises.id", ondelete="CASCADE"), nullable=True),
        sa.Column("source_family", sa.String(40), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connection_id", "dedupe_hash", name="uq_health_hr_aggregate_dedupe"),
        sa.CheckConstraint("end_at > start_at", name="ck_health_hr_aggregate_interval"),
        sa.CheckConstraint("min_bpm >= 20 AND max_bpm <= 300 AND min_bpm <= avg_bpm AND avg_bpm <= max_bpm", name="ck_health_hr_aggregate_values"),
    )
    op.create_index("ix_health_heart_rate_aggregates_connection_id", "health_heart_rate_aggregates", ["connection_id"])
    op.create_index("ix_health_heart_rate_aggregates_user_id", "health_heart_rate_aggregates", ["user_id"])
    op.create_index("ix_health_heart_rate_aggregates_sleep_session_id", "health_heart_rate_aggregates", ["sleep_session_id"])
    op.create_index("ix_health_heart_rate_aggregates_exercise_id", "health_heart_rate_aggregates", ["exercise_id"])
    op.create_index("ix_health_hr_user_grain_start", "health_heart_rate_aggregates", ["user_id", "granularity", "start_at"])

    op.create_table(
        "health_heart_rate_zones",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("health_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("zone_type", sa.String(30), nullable=False),
        sa.Column("min_bpm", sa.Integer(), nullable=False),
        sa.Column("max_bpm", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connection_id", "local_date", "zone_type", name="uq_health_hr_zone_day"),
        sa.CheckConstraint("min_bpm >= 20 AND max_bpm <= 300 AND min_bpm <= max_bpm", name="ck_health_hr_zone_values"),
    )
    op.create_index("ix_health_heart_rate_zones_connection_id", "health_heart_rate_zones", ["connection_id"])
    op.create_index("ix_health_heart_rate_zones_user_id", "health_heart_rate_zones", ["user_id"])

    op.create_table(
        "health_data_gaps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("health_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_type", sa.String(80), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connection_id", "data_type", "local_date", name="uq_health_gap_day"),
    )
    op.create_index("ix_health_data_gaps_connection_id", "health_data_gaps", ["connection_id"])
    op.create_index("ix_health_data_gaps_user_id", "health_data_gaps", ["user_id"])


def downgrade() -> None:
    for table in (
        "health_data_gaps",
        "health_heart_rate_zones",
        "health_heart_rate_aggregates",
        "health_exercises",
        "health_sleep_stages",
        "health_sleep_sessions",
        "health_metrics",
        "health_sync_cursors",
        "health_sync_runs",
        "health_data_sources",
        "health_oauth_states",
        "health_connections",
    ):
        op.drop_table(table)
