"""create holding table for portfolio tracking

Revision ID: a1b2c3d4e5f6
Revises: be8fd5d5b9e7
Create Date: 2026-07-01 12:00:00.000000

Sprint 2 — portfolio feature: a `holding` table that lets users
track investment holdings (stocks, ETFs, crypto, etc.) manually.
Linked to `account` via an optional FK so investment accounts
discovered via open-banking sync can later feed into portfolio
aggregation without a schema change.

Cascade spine (same constraint as data-layer migration):
    users -> bank_connection -> account -> transaction   (all CASCADE)
    users -> category                                      (CASCADE)
    users -> budget                                        (CASCADE)
    users -> holding                                       (CASCADE)

`holding.account_id` is NO ACTION — deleting an account leaves
its manual holdings intact (user may want to keep tracking them
after unlinking the bank).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "be8fd5d5b9e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "holding",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("account_id", sa.Uuid(), nullable=True, index=True),
        sa.Column("symbol", sa.Unicode(20), nullable=False, index=True),
        sa.Column("name", sa.Unicode(255), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum("stock", "etf", "mutual_fund", "bond", "crypto", "cash", "other",
                    name="asset_type", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("currency", sa.Unicode(3), nullable=False),
        sa.Column("quantity", sa.Numeric(19, 8), nullable=False),
        sa.Column("cost_basis", sa.Numeric(19, 4), nullable=True),
        sa.Column("current_price", sa.Numeric(19, 6), nullable=True),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Unicode(1000), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"], ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("holding")
    op.execute("DROP TYPE asset_type")
