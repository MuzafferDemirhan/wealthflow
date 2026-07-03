"""create data layer tables (category, bank_connection, account, transaction, budget)

Revision ID: be8fd5d5b9e7
Revises: aa4ceb322f08
Create Date: 2026-07-01 00:00:00.000000

Sprint 2 - data layer schema for open-banking sync, transaction
ingestion, ML categorization, and budgets.

Table names are singular by convention (`category`, not `categories`),
matching the models. Two of them are SQL Server reserved words -
`transaction` (T-SQL statement) - which SQLAlchemy automatically
bracket-quotes (`[transaction]`) in every DDL/DML statement it emits,
so this is handled transparently as long as all access goes through
SQLAlchemy/Alembic. The existing Sprint 1 tables (`users`,
`refresh_tokens`) are intentionally left plural/unchanged here - they
belong to an already-merged migration; renaming them (`user` is also
a T-SQL reserved word, used as a niladic function) is a separate
decision tracked outside this revision.

NOTE: authored by hand (no live MS SQL Server instance reachable in
this environment), same as aa4ceb322f08. Each table's DDL was
compiled against `sqlalchemy.dialects.mssql` and validated end-to-end
against an in-memory SQLite engine via `Base.metadata.create_all()`.

IMPORTANT - cascade design: several FKs below deliberately omit
`ondelete=CASCADE`/`SET NULL` even where it would be semantically
natural, because SQL Server refuses to create a schema where a table
is reachable via more than one cascading path from the same root, or
where a self-referencing FK carries a cascading action on a table
that's also reachable via cascade from elsewhere (error 1785:
"may cause cycles or multiple cascade paths"). The single cascade
spine kept is:
    users -> bank_connection -> account -> transaction   (all CASCADE)
    users -> category                                      (CASCADE)
    users -> budget                                        (CASCADE)
`account.user_id`, `category.parent_id`, `transaction.category_id`,
and `budget.category_id` are NO ACTION - cleanup across those edges
(e.g. deleting a category that budgets/transactions still reference)
is the service layer's responsibility, not the database's.

Run `alembic upgrade head` against a real SQL Server 2022 instance to
confirm end-to-end before relying on it in CI/staging.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "be8fd5d5b9e7"
down_revision: str | None = "aa4ceb322f08"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # --- category -------------------------------------------------
    op.create_table(
        "category",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.Unicode(length=100), nullable=False),
        sa.Column("slug", sa.Unicode(length=100), nullable=False),
        sa.Column("icon", sa.Unicode(length=50), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("parent_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_category"),
        sa.UniqueConstraint("slug", name="uq_category_slug"),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["category.id"], name="fk_category_parent_id_category"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_category_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_category_parent_id", "category", ["parent_id"])
    op.create_index("ix_category_user_id", "category", ["user_id"])

    # --- bank_connection --------------------------------------------
    op.create_table(
        "bank_connection",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("institution_id", sa.Unicode(length=100), nullable=False),
        sa.Column("institution_name", sa.Unicode(length=255), nullable=False),
        sa.Column("external_reference", sa.Unicode(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("consent_expires_at", sa.Date(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_bank_connection"),
        sa.UniqueConstraint(
            "external_reference", name="uq_bank_connection_external_reference"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_bank_connection_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_bank_connection_user_id", "bank_connection", ["user_id"])

    # --- account ------------------------------------------------------
    op.create_table(
        "account",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("bank_connection_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("external_account_id", sa.Unicode(length=255), nullable=False),
        sa.Column("display_name", sa.Unicode(length=255), nullable=False),
        sa.Column(
            "account_type",
            sa.String(length=20),
            nullable=False,
            server_default="other",
        ),
        sa.Column("iban", sa.Unicode(length=34), nullable=True),
        sa.Column("currency", sa.Unicode(length=3), nullable=False),
        sa.Column(
            "current_balance",
            sa.Numeric(precision=19, scale=4),
            nullable=False,
            server_default="0",
        ),
        sa.Column("balance_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id", name="pk_account"),
        sa.UniqueConstraint(
            "external_account_id", name="uq_account_external_account_id"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_account_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["bank_connection_id"],
            ["bank_connection.id"],
            name="fk_account_bank_connection_id_bank_connection",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_account_user_id", "account", ["user_id"])
    op.create_index("ix_account_bank_connection_id", "account", ["bank_connection_id"])

    # --- transaction ----------------------------------------------
    # NOTE: "transaction" is a T-SQL reserved word (BEGIN TRANSACTION,
    # etc.). `op.create_table` + SQLAlchemy's mssql IdentifierPreparer
    # bracket-quote it (`[transaction]`) automatically in every
    # statement they emit, so no special handling is needed here.
    op.create_table(
        "transaction",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("category_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("external_id", sa.Unicode(length=255), nullable=True),
        sa.Column("dedupe_hash", sa.Unicode(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("currency", sa.Unicode(length=3), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="booked",
        ),
        sa.Column(
            "description", sa.Unicode(length=500), nullable=False, server_default=""
        ),
        sa.Column("counterparty_name", sa.Unicode(length=255), nullable=True),
        sa.Column("category_source", sa.String(length=10), nullable=True),
        sa.Column("category_confidence", sa.Float(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_transaction"),
        sa.UniqueConstraint(
            "account_id", "dedupe_hash", name="uq_transaction_account_dedupe"
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["account.id"],
            name="fk_transaction_account_id_account",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["category.id"],
            name="fk_transaction_category_id_category",
        ),
    )
    op.create_index("ix_transaction_account_id", "transaction", ["account_id"])
    op.create_index("ix_transaction_category_id", "transaction", ["category_id"])
    op.create_index("ix_transaction_external_id", "transaction", ["external_id"])
    op.create_index("ix_transaction_booking_date", "transaction", ["booking_date"])

    # --- budget -----------------------------------------------------
    op.create_table(
        "budget",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("category_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("amount_limit", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("currency", sa.Unicode(length=3), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_budget"),
        sa.UniqueConstraint(
            "user_id",
            "category_id",
            "period_month",
            name="uq_budget_user_category_period",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_budget_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["category.id"], name="fk_budget_category_id_category"
        ),
    )
    op.create_index("ix_budget_user_id", "budget", ["user_id"])
    op.create_index("ix_budget_category_id", "budget", ["category_id"])
    op.create_index("ix_budget_period_month", "budget", ["period_month"])


def downgrade() -> None:
    op.drop_index("ix_budget_period_month", table_name="budget")
    op.drop_index("ix_budget_category_id", table_name="budget")
    op.drop_index("ix_budget_user_id", table_name="budget")
    op.drop_table("budget")

    op.drop_index("ix_transaction_booking_date", table_name="transaction")
    op.drop_index("ix_transaction_external_id", table_name="transaction")
    op.drop_index("ix_transaction_category_id", table_name="transaction")
    op.drop_index("ix_transaction_account_id", table_name="transaction")
    op.drop_table("transaction")

    op.drop_index("ix_account_bank_connection_id", table_name="account")
    op.drop_index("ix_account_user_id", table_name="account")
    op.drop_table("account")

    op.drop_index("ix_bank_connection_user_id", table_name="bank_connection")
    op.drop_table("bank_connection")

    op.drop_index("ix_category_user_id", table_name="category")
    op.drop_index("ix_category_parent_id", table_name="category")
    op.drop_table("category")
