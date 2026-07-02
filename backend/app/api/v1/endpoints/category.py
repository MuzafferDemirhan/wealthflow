from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.category import CategoryRead
from app.services import category_service

router = APIRouter()


@router.get("", response_model=list[CategoryRead])
async def list_categories(
    db: Session = Depends(get_db),
):
    """List all system categories (FR — ML categorization, budgets)."""
    return category_service.get_all_categories(db)


@router.get("/{slug}", response_model=CategoryRead)
async def get_category_by_slug(
    slug: str,
    db: Session = Depends(get_db),
):
    """Get a single category by its slug (e.g. "groceries", "income")."""
    try:
        return category_service.get_category_by_slug(db, slug=slug)
    except category_service.CategoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{slug}' not found",
        )
