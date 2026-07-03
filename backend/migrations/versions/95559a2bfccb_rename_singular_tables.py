"""rename users -> user, refresh_tokens -> refresh_token (singular table names)

Revision ID: 95559a2bfccb
Revises: a1b2c3d4e5f6
Create Date: 2026-07-01 01:00:00.000000

Brings the Sprint 1 tables in line with the singular naming
convention adopted for the Sprint 2 data layer (`category`,
`bank_connection`, `account`, `transaction`, `budget`, `holding`).

This is a *separate* migration rather than an edit to `aa4ceb322f08`
(which created `users`/`refresh_tokens`) because that revision is
already merged to `main` - any environment that has already run it
has physical tables named `users`/`refresh_tokens`. Rewriting that
migration's DDL in place would silently diverge for those
environments (Alembic tracks applied state by revision id, not by
diffing DDL, so it would never notice or fix the mismatch). A rename
migration is the correct, environment-safe way to get everyone to
the same end state.

Uses `op.rename_table`, which Alembic's MSSQL dialect implementation
compiles to `EXEC sp_rename` - this preserves the underlying object
id, so existing foreign keys (`refresh_token.user_id`, and every FK
added in `be8fd5d5b9e7`/`a1b2c3d4e5f6` referencing `users.id`:
`category.user_id`, `bank_connection.user_id`, `account.user_id`,
`budget.user_id`, `holding.user_id`) keep working without being
recreated; only the constraint/index *names* below are stale after
the table rename and are renamed to match the naming convention's
new output (`pk_user`, `ix_user_email`, `fk_category_user_id_user`,
etc).

`user` is a T-SQL reserved word (used as a niladic function), same
situation as `transaction` in `be8fd5d5b9e7` - SQLAlchemy/Alembic
bracket-quote it automatically wherever needed, and `sp_rename`
receives it as a plain string parameter (not parsed as an
identifier), so no quoting is required in the raw SQL below either.

NOTE: authored by hand - `EXEC sp_rename` is MSSQL-specific T-SQL and
cannot be exercised against the SQLite fixture used to sanity-check
the other migrations in this project. Run this against a real SQL
Server 2022 instance (`docker compose up mssql mssql_init && alembic
upgrade head`) before relying on it in CI/staging.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "95559a2bfccb"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # --- users -> user -------------------------------------------------
    op.rename_table("users", "user")
    op.execute("EXEC sp_rename N'pk_users', N'pk_user', N'OBJECT'")
    op.execute("EXEC sp_rename N'user.ix_users_email', N'ix_user_email', N'INDEX'")

    # --- refresh_tokens -> refresh_token ---------------------------------
    op.rename_table("refresh_tokens", "refresh_token")
    op.execute("EXEC sp_rename N'pk_refresh_tokens', N'pk_refresh_token', N'OBJECT'")
    op.execute(
        "EXEC sp_rename N'uq_refresh_tokens_token_hash', "
        "N'uq_refresh_token_token_hash', N'OBJECT'"
    )
    op.execute(
        "EXEC sp_rename N'fk_refresh_tokens_user_id_users', "
        "N'fk_refresh_token_user_id_user', N'OBJECT'"
    )
    op.execute(
        "EXEC sp_rename N'refresh_token.ix_refresh_tokens_user_id', "
        "N'ix_refresh_token_user_id', N'INDEX'"
    )

    # --- FK constraint names on tables referencing users.id ---------
    # (created in be8fd5d5b9e7 / a1b2c3d4e5f6, still carrying the old
    # `..._users` suffix even though the FK itself kept working
    # through the table rename above)
    for fk in [
        "fk_category_user_id_users",
        "fk_bank_connection_user_id_users",
        "fk_account_user_id_users",
        "fk_budget_user_id_users",
        "fk_holding_user_id_users",
    ]:
        new_fk = fk.replace("_users", "_user")
        op.execute(f"EXEC sp_rename N'{fk}', N'{new_fk}', N'OBJECT'")


def downgrade() -> None:
    # --- FK constraint names on tables referencing users.id ---------
    for fk in [
        "fk_category_user_id_users",
        "fk_bank_connection_user_id_users",
        "fk_account_user_id_users",
        "fk_budget_user_id_users",
        "fk_holding_user_id_users",
    ]:
        new_fk = fk.replace("_users", "_user")
        op.execute(f"EXEC sp_rename N'{new_fk}', N'{fk}', N'OBJECT'")

    # --- refresh_token -> refresh_tokens ---------------------------------
    op.execute(
        "EXEC sp_rename N'refresh_token.ix_refresh_token_user_id', "
        "N'ix_refresh_tokens_user_id', N'INDEX'"
    )
    op.execute(
        "EXEC sp_rename N'fk_refresh_token_user_id_user', "
        "N'fk_refresh_tokens_user_id_users', N'OBJECT'"
    )
    op.execute(
        "EXEC sp_rename N'uq_refresh_token_token_hash', "
        "N'uq_refresh_tokens_token_hash', N'OBJECT'"
    )
    op.execute("EXEC sp_rename N'pk_refresh_token', N'pk_refresh_tokens', N'OBJECT'")
    op.rename_table("refresh_token", "refresh_tokens")

    # --- user -> users ---------------------------------------------------
    op.execute("EXEC sp_rename N'user.ix_user_email', N'ix_users_email', N'INDEX'")
    op.execute("EXEC sp_rename N'pk_user', N'pk_users', N'OBJECT'")
    op.rename_table("user", "users")
