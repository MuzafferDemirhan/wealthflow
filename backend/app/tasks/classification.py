"""Celery task that applies the ML classifier to a single transaction."""

import uuid

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.ml.classifier import train_default
from app.models.category import Category
from app.models.transaction import CategorySource, Transaction

# Lazy-loaded singleton — trained once per worker process
_CLASSIFIER = None


def _get_classifier():
    global _CLASSIFIER
    if _CLASSIFIER is None:
        _CLASSIFIER = train_default()
    return _CLASSIFIER


def _reset_classifier():
    """Force retrain on next call (used after user corrections)."""
    global _CLASSIFIER
    _CLASSIFIER = None


@celery_app.task(name="ingestion.classify_transaction", bind=True, max_retries=2)
def classify_transaction(self, transaction_id: str) -> dict:
    """Predict category for a transaction and persist the result.

    Runs the ML classifier on a single transaction. If the prediction
    confidence exceeds the threshold, ``category_id``, ``category_source``
    and ``category_confidence`` are updated in place.

    Returns a dict with the prediction result or error info.
    """
    db = SessionLocal()
    try:
        txn_id = uuid.UUID(transaction_id)
    except ValueError:
        return {"ok": False, "error": f"invalid transaction_id: {transaction_id}"}

    try:
        stmt = select(Transaction).where(Transaction.id == txn_id)
        txn = db.scalar(stmt)
        if txn is None:
            return {"ok": False, "error": "transaction not found"}

        # Skip if user has already assigned a category
        if txn.category_source == CategorySource.USER:
            return {"ok": True, "slug": None, "source": "user", "note": "already categorized by user"}

        clf = _get_classifier()
        result = clf.predict(
            description=txn.description,
            counterparty_name=txn.counterparty_name,
            amount=float(txn.amount),
        )

        slug = result["slug"]
        source_str = result["source"]
        confidence = result["confidence"]

        if slug and source_str and slug != "other":
            source = CategorySource(source_str)
            cat_stmt = select(Category).where(Category.slug == slug)
            category = db.scalar(cat_stmt)

            if category is not None:
                txn.category_id = category.id
                txn.category_source = source
                txn.category_confidence = confidence
                db.add(txn)
                db.commit()
                return {
                    "ok": True,
                    "slug": slug,
                    "confidence": confidence,
                    "source": source_str,
                }

        return {
            "ok": True,
            "slug": None,
            "confidence": confidence,
            "source": source_str,
            "note": "no category assigned (low confidence or uncategorizable)",
        }
    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(name="ingestion.retrain_classifier")
def retrain_classifier() -> None:
    """Rebuild the ML model from the current seed data.

    Call this after a batch of user corrections to keep the model
    up to date.
    """
    _reset_classifier()
    _get_classifier()
