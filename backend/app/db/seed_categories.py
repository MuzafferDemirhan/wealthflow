"""Insert default system categories into the database."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.seed_data import CATEGORY_SEED_DATA
from app.models.category import Category


def seed_categories(db: Session) -> list[Category]:
    """Idempotently insert seed categories and return all system categories.

    Skips slugs that already exist so repeated calls are safe.
    Parent references are resolved after bulk-insert so self-referential
    FKs work regardless of insertion order.
    """
    existing = _load_slug_map(db)
    created: list[Category] = []

    for entry in CATEGORY_SEED_DATA:
        if entry["slug"] in existing:
            continue
        cat = Category(
            id=uuid.uuid4(),
            name=entry["name"],
            slug=entry["slug"],
            icon=entry.get("icon"),
            is_system=True,
            user_id=None,
            parent_id=None,
        )
        db.add(cat)
        created.append(cat)

    if created:
        db.flush()

    # Resolve parent references for newly created rows
    slug_map = _load_slug_map(db)
    for entry, cat in zip(CATEGORY_SEED_DATA, created):
        parent_slug = entry.get("parent_slug")
        if parent_slug and parent_slug in slug_map:
            cat.parent_id = slug_map[parent_slug].id
            db.add(cat)

    if created:
        db.commit()

    return list(_load_slug_map(db).values())


def _load_slug_map(db: Session) -> dict[str, Category]:
    stmt = select(Category).where(Category.is_system)
    return {c.slug: c for c in db.scalars(stmt).all()}
