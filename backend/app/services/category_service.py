import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category


class CategoryNotFoundError(Exception):
    pass


def get_all_categories(db: Session) -> list[Category]:
    stmt = select(Category).order_by(Category.name)
    return list(db.scalars(stmt).all())


def get_category(db: Session, *, category_id: uuid.UUID) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise CategoryNotFoundError()
    return category
