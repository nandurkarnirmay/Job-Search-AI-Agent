"""Weeks 5-6: calendar events + private feed token, skill-progress tracking, GitHub username on profile

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-15
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("calendar_token", sa.String(64), nullable=True))
        batch.create_unique_constraint("uq_users_calendar_token", ["calendar_token"])
    with op.batch_alter_table("profiles") as batch:
        batch.add_column(sa.Column("github_username", sa.String(39), nullable=True))

    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("remind", sa.Boolean(), nullable=False),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_calendar_events_user_id", "calendar_events", ["user_id"])
    op.create_index("ix_calendar_events_starts_at", "calendar_events", ["starts_at"])

    op.create_table(
        "skill_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill", sa.String(60), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "skill", name="uq_skill_progress_user_skill"),
    )
    op.create_index("ix_skill_progress_user_id", "skill_progress", ["user_id"])


def downgrade() -> None:
    op.drop_table("skill_progress")
    op.drop_table("calendar_events")
    with op.batch_alter_table("profiles") as batch:
        batch.drop_column("github_username")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_calendar_token", type_="unique")
        batch.drop_column("calendar_token")
