"""
Import every ORM model here so that:

1. Alembic's `target_metadata = Base.metadata` sees all tables during
   autogeneration (a model that is never imported never registers
   itself with `Base.metadata`).
2. `relationship("User")` / `relationship("RefreshToken")` string
   references resolve correctly regardless of import order elsewhere
   in the app.
"""

from app.db.base_class import Base  # noqa: F401
from app.models.account import Account, AccountType  # noqa: F401
from app.models.bank_connection import (  # noqa: F401
    BankConnection,
    BankProvider,
    ConnectionStatus,
)
from app.models.budget import Budget  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.chat_message import ChatMessage  # noqa: F401
from app.models.export import Export, ExportFormat, ExportStatus  # noqa: F401
from app.models.holding import AssetType, Holding  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.transaction import (  # noqa: F401
    CategorySource,
    Transaction,
    TransactionStatus,
)
from app.models.user import User, UserRole  # noqa: F401

__all__ = [
    "Base",
    "User",
    "UserRole",
    "RefreshToken",
    "BankConnection",
    "BankProvider",
    "ConnectionStatus",
    "Account",
    "AccountType",
    "Category",
    "Transaction",
    "TransactionStatus",
    "CategorySource",
    "Budget",
    "Holding",
    "AssetType",
    "ChatMessage",
    "Export",
    "ExportFormat",
    "ExportStatus",
    "Notification",
]
