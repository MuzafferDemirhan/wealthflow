"""rename user table to user_account (avoids T-SQL reserved word conflicts)

Revision ID: d5e6f7a8b9c0
Revises: 95559a2bfccb
Create Date: 2026-07-05 17:00:00.000000

``user`` is a T-SQL niladic function (``SELECT USER``) and while
SQLAlchemy bracket-quotes it automatically, several ORM features
(relationship secondary, Alembic autogenerate diffing, etc.) struggle
with it unless explicit ``quote=True`` is scattered everywhere.
Renaming to ``user_account`` eliminates the friction entirely.

This is a pure metadata rename (``sp_rename`` on the table, then on
each constraint / index whose name contains ``_user`` that should now
read ``_user_account``).  The FK constraint *names* were already
updated from ``_users`` to ``_user`` in ``95559a2bfccb``; this revision
updates them again to ``_user_account``.

NOTE: authored by hand - ``EXEC sp_rename`` is MSSQL-specific T-SQL and
cannot be exercised against the SQLite fixture used to sanity-check
the other migrations in this project.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "95559a2bfccb"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # --- user -> user_account -------------------------------------------
    op.rename_table("user", "user_account")
    op.execute("EXEC sp_rename N'pk_user', N'pk_user_account', N'OBJECT'")
    op.execute("EXEC sp_rename N'user_account.ix_user_email', N'ix_user_account_email', N'INDEX'")

    # --- FK constraints referencing user.id -----------------------------
    for fk in [
        "fk_refresh_token_user_id_user",
        "fk_category_user_id_user",
        "fk_bank_connection_user_id_user",
        "fk_account_user_id_user",
        "fk_budget_user_id_user",
        "fk_holding_user_id_user",
    ]:
        new_fk = fk.replace("_user", "_user_account")
        op.execute(f"EXEC sp_rename N'{fk}', N'{new_fk}', N'OBJECT'")


def downgrade() -> None:
    # --- FK constraints referencing user_account.id --------------------
    for fk in [
        "fk_refresh_token_user_id_user_account",
        "fk_category_user_id_user_account",
        "fk_bank_connection_user_id_user_account",
        "fk_account_user_id_user_account",
        "fk_budget_user_id_user_account",
        "fk_holding_user_id_user_account",
    ]:
        old_fk = fk.replace("_user_account", "_user")
        op.execute(f"EXEC sp_rename N'{fk}', N'{old_fk}', N'OBJECT'")

    # --- user_account -> user -------------------------------------------
    op.execute("EXEC sp_rename N'user_account.ix_user_account_email', N'ix_user_email', N'INDEX'")
    op.execute("EXEC sp_rename N'pk_user_account', N'pk_user', N'OBJECT'")
    op.rename_table("user_account", "user")
