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
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401

__all__ = ["Base", "User", "UserRole", "RefreshToken"]
