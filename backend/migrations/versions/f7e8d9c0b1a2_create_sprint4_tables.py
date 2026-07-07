"""create sprint 4 tables (chat_message, notification, export)

Revision ID: f7e8d9c0b1a2
Revises: d5e6f7a8b9c0
Create Date: 2026-07-07 00:00:00.000000

Sprint 4 — chatbot, export, and WebSocket notification tables.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7e8d9c0b1a2"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # --- chat_message -------------------------------------------------
    op.create_table(
        "chat_message",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("conversation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_chat_message"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_chat_message_user_id_user_account",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_chat_message_user_id", "chat_message", ["user_id"])
    op.create_index("ix_chat_message_conversation_id", "chat_message", ["conversation_id"])

    # --- notification ------------------------------------------------
    op.create_table(
        "notification",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id", name="pk_notification"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_notification_user_id_user_account",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_notification_user_id", "notification", ["user_id"])

    # --- export ------------------------------------------------------
    op.create_table(
        "export",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False),
        sa.Column("report_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="processing"),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_export"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_export_user_id_user_account",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_export_user_id", "export", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_export_user_id", table_name="export")
    op.drop_table("export")

    op.drop_index("ix_notification_user_id", table_name="notification")
    op.drop_table("notification")

    op.drop_index("ix_chat_message_conversation_id", table_name="chat_message")
    op.drop_index("ix_chat_message_user_id", table_name="chat_message")
    op.drop_table("chat_message")
