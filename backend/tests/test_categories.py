import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.seed_categories import seed_categories
from app.main import app
from app.ml.seed_data import CATEGORY_SEED_DATA
from app.models.category import Category
from app.models.user import User, UserRole

# ------------------------------------------------------------------
# Unit: seed_categories
# ------------------------------------------------------------------


class TestSeedCategories:
    def test_seeds_all_categories(self, db_session):
        cats = seed_categories(db_session)
        assert len(cats) == len(CATEGORY_SEED_DATA)

    def test_all_are_system_categories(self, db_session):
        cats = seed_categories(db_session)
        assert all(c.is_system for c in cats)

    def test_no_user_id_on_system_categories(self, db_session):
        cats = seed_categories(db_session)
        assert all(c.user_id is None for c in cats)

    def test_idempotent(self, db_session):
        first = seed_categories(db_session)
        second = seed_categories(db_session)
        assert len(first) == len(second) == len(CATEGORY_SEED_DATA)

    def test_slug_uniqueness(self, db_session):
        cats = seed_categories(db_session)
        slugs = [c.slug for c in cats]
        assert len(slugs) == len(set(slugs))

    def test_individual_fields(self, db_session):
        cats = seed_categories(db_session)
        lookup = {c.slug: c for c in cats}

        income = lookup["income"]
        assert income.name == "Income"
        assert income.icon == "trending-up"

        groceries = lookup["groceries"]
        assert groceries.name == "Groceries"
        assert groceries.icon == "shopping-cart"

        other = lookup["other"]
        assert other.name == "Other"

    def test_repeated_seed_does_not_create_duplicates(self, db_session):
        seed_categories(db_session)
        seed_categories(db_session)
        seed_categories(db_session)
        stmt = select(Category)
        count = len(list(db_session.scalars(stmt).all()))
        assert count == len(CATEGORY_SEED_DATA)


# ------------------------------------------------------------------
# Integration: category API endpoints
# ------------------------------------------------------------------


class TestCategoryAPI:
    def test_list_categories_returns_all_seeded(self, db_session, client):
        seed_categories(db_session)
        response = client.get("/api/v1/category")
        assert response.status_code == 200
        data = response.json()
        slugs = {c["slug"] for c in data}
        expected = {d["slug"] for d in CATEGORY_SEED_DATA}
        assert slugs == expected

    def test_list_categories_includes_icon_and_name(self, db_session, client):
        seed_categories(db_session)
        response = client.get("/api/v1/category")
        data = response.json()
        for cat in data:
            assert "id" in cat
            assert "name" in cat
            assert "slug" in cat
            assert "icon" in cat
            assert "is_system" in cat
            assert cat["is_system"] is True

    def test_get_category_by_slug_found(self, db_session, client):
        seed_categories(db_session)
        response = client.get("/api/v1/category/groceries")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "groceries"
        assert data["name"] == "Groceries"

    def test_get_category_by_slug_not_found(self, db_session, client):
        seed_categories(db_session)
        response = client.get("/api/v1/category/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_categories_empty_db(self, db_session, client):
        response = client.get("/api/v1/category")
        assert response.status_code == 200
        assert response.json() == []


# ------------------------------------------------------------------
# Service layer
# ------------------------------------------------------------------


class TestCategoryService:
    def test_get_category_by_slug(self, db_session):
        seed_categories(db_session)
        from app.services.category_service import get_category_by_slug

        cat = get_category_by_slug(db_session, slug="income")
        assert cat.slug == "income"
        assert cat.name == "Income"

    def test_get_category_by_slug_raises_not_found(self, db_session):
        from app.services.category_service import (
            CategoryNotFoundError,
            get_category_by_slug,
        )

        with pytest.raises(CategoryNotFoundError):
            get_category_by_slug(db_session, slug="does-not-exist")

    def test_get_category_by_id(self, db_session):
        seed_categories(db_session)
        from app.services.category_service import get_category

        stmt = select(Category).where(Category.slug == "utilities")
        cat = db_session.scalar(stmt)
        fetched = get_category(db_session, category_id=cat.id)
        assert fetched.id == cat.id
        assert fetched.slug == "utilities"



