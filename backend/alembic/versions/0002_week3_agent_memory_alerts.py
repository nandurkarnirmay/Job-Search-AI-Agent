"""Week 3: career-goal profile fields, chat threads/messages (agent memory), job alerts

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-23
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("profiles") as batch:
        batch.add_column(sa.Column("career_goal", sa.Text(), nullable=True))
        batch.add_column(sa.Column("target_roles", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("open_to_relocation", sa.Boolean(), nullable=True))

    op.create_table(
        "chat_threads",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(80), nullable=False),
        sa.Column("last_params", sa.JSON(), nullable=True),
        sa.Column("last_jobs", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_threads_user_id", "chat_threads", ["user_id"])
    op.create_index("ix_chat_threads_updated_at", "chat_threads", ["updated_at"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thread_id", sa.String(32), sa.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(20), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_messages_thread_id", "chat_messages", ["thread_id"])

    op.create_table(
        "job_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("frequency", sa.String(10), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("seen_keys", sa.JSON(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_alerts_user_id", "job_alerts", ["user_id"])


def downgrade() -> None:
    op.drop_table("job_alerts")
    op.drop_table("chat_messages")
    op.drop_table("chat_threads")
    with op.batch_alter_table("profiles") as batch:
        batch.drop_column("open_to_relocation")
        batch.drop_column("target_roles")
        batch.drop_column("career_goal")
