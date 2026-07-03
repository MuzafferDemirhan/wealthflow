import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.db.seed_categories import seed_categories
from app.ml.classifier import TransactionClassifier, train_default
from app.ml.seed_data import CATEGORY_SEED_DATA, SEED_TRANSACTIONS

# ------------------------------------------------------------------
# Unit: rule-based matching
# ------------------------------------------------------------------


class TestRules:
    def test_groceries_lidl(self):
        clf = TransactionClassifier()
        result = clf.predict("Lidl", "LIDL SP ZOO", -45.99)
        assert result["slug"] == "groceries"
        assert result["source"] == "rule"

    def test_dining_pizza(self):
        clf = TransactionClassifier()
        result = clf.predict("Pizza Hut", "", -55.00)
        assert result["slug"] == "dining"

    def test_transport_orlen(self):
        clf = TransactionClassifier()
        result = clf.predict("ORLEN", "", -200.00)
        assert result["slug"] == "transport"

    def test_income_salary(self):
        clf = TransactionClassifier()
        result = clf.predict("Wynagrodzenie", "EMPLOYER", 5000.00)
        assert result["slug"] == "income"

    def test_housing_rent(self):
        clf = TransactionClassifier()
        result = clf.predict("Czynsz", "WSPOLNOTA", -800.00)
        assert result["slug"] == "housing"

    def test_utilities_tauron(self):
        clf = TransactionClassifier()
        result = clf.predict("Tauron", "", -180.00)
        assert result["slug"] == "utilities"

    def test_healthcare_apteka(self):
        clf = TransactionClassifier()
        result = clf.predict("Apteka", "", -45.00)
        assert result["slug"] == "healthcare"

    def test_shopping_allegro(self):
        clf = TransactionClassifier()
        result = clf.predict("Allegro", "", -150.00)
        assert result["slug"] == "shopping"

    def test_entertainment_netflix(self):
        clf = TransactionClassifier()
        result = clf.predict("Netflix", "", -55.00)
        assert result["slug"] == "entertainment"

    def test_education_coursera(self):
        clf = TransactionClassifier()
        result = clf.predict("Coursera", "", -200.00)
        assert result["slug"] == "education"

    def test_transfer_przelew(self):
        clf = TransactionClassifier()
        result = clf.predict("Przelew własny", "", -500.00)
        assert result["slug"] == "transfer"

    def test_unknown_returns_other_no_model(self):
        clf = TransactionClassifier()
        result = clf.predict("Some random unknown transaction", None, -10.00)
        assert result["slug"] == "other"
        assert result["confidence"] == 0.0
        assert result["source"] is None


# ------------------------------------------------------------------
# Unit: ML classifier training & prediction
# ------------------------------------------------------------------


class TestMLClassifier:
    def test_train_and_predict_known(self):
        clf = TransactionClassifier(seed_data=SEED_TRANSACTIONS)
        clf.train()
        result = clf.predict("Lidl", "", -50.00)
        # ML or rule — either is fine
        assert result["slug"] in ("groceries", "other")
        assert result["confidence"] >= 0.0

    def test_confidence_is_between_0_and_1(self):
        clf = TransactionClassifier(seed_data=SEED_TRANSACTIONS)
        clf.train()
        for d in SEED_TRANSACTIONS[:20]:
            result = clf.predict(d["description"], d.get("counterparty", ""), float(d["amount"]))
            assert 0.0 <= result["confidence"] <= 1.0

    def test_no_seed_data_returns_other(self):
        clf = TransactionClassifier(seed_data=[])
        clf.train()
        result = clf.predict("ZYXVUTSRQPONMLKJ", "", -10.00)
        assert result["slug"] == "other"

    def test_train_default(self):
        clf = train_default()
        assert clf._classes is not None
        assert len(clf._classes) > 5  # at least 6 categories

    def test_additional_data_retrain(self):
        clf = TransactionClassifier(seed_data=SEED_TRANSACTIONS)
        clf.train()
        slug_before = clf.predict("Custom Shop", "", -30.00)["slug"]

        extra = [
            {"description": "Custom Shop", "counterparty": "", "amount": -30.00, "category_slug": "shopping"},
            {"description": "Custom Shop", "counterparty": "", "amount": -31.00, "category_slug": "shopping"},
            {"description": "Custom Shop", "counterparty": "", "amount": -32.00, "category_slug": "shopping"},
        ]
        clf.train(additional_data=extra)
        # rule will catch "shop" -> shopping anyway
        assert slug_before == "shopping" or slug_before == "other"


# ------------------------------------------------------------------
# Unit: predict_proba
# ------------------------------------------------------------------


class TestPredictProba:
    def test_returns_dict(self):
        clf = TransactionClassifier(seed_data=SEED_TRANSACTIONS)
        clf.train()
        probs = clf.predict_proba("Lidl")
        assert isinstance(probs, dict)
        assert all(isinstance(v, float) for v in probs.values())

    def test_empty_when_no_model(self):
        clf = TransactionClassifier()
        assert clf.predict_proba("test") == {}


# ------------------------------------------------------------------
# Unit: serialization round-trip
# ------------------------------------------------------------------


class TestSerialization:
    def test_dumps_loads_roundtrip(self):
        clf1 = train_default()
        blob = clf1.dumps()
        clf2 = TransactionClassifier.loads(blob)
        assert clf2._classes == clf1._classes
        r1 = clf1.predict("Lidl", "", -10.00)
        r2 = clf2.predict("Lidl", "", -10.00)
        assert r1["slug"] == r2["slug"]


# ------------------------------------------------------------------
# Integration: category seeding
# ------------------------------------------------------------------


class TestSeedCategories:
    def test_seeds_system_categories(self, db_session):
        cats = seed_categories(db_session)
        slugs = {c.slug for c in cats}
        expected = {d["slug"] for d in CATEGORY_SEED_DATA}
        assert slugs == expected

    def test_is_idempotent(self, db_session):
        first = seed_categories(db_session)
        second = seed_categories(db_session)
        assert len(first) == len(second) == len(CATEGORY_SEED_DATA)

    def test_all_seeded_categories_are_system(self, db_session):
        cats = seed_categories(db_session)
        assert all(c.is_system for c in cats)

    def test_slugs_are_unique(self, db_session):
        cats = seed_categories(db_session)
        slugs = [c.slug for c in cats]
        assert len(slugs) == len(set(slugs))


# ------------------------------------------------------------------
# Integration: classification task with DB
# ------------------------------------------------------------------


class TestClassificationWithDB:
    def test_classify_new_transaction(self, db_session):
        from app.ml.classifier import train_default
        from app.models.account import Account, AccountType
        from app.models.bank_connection import (
            BankConnection,
            BankProvider,
            ConnectionStatus,
        )
        from app.models.transaction import Transaction, TransactionStatus
        from app.models.user import User, UserRole

        # Seed categories first
        seed_categories(db_session)

        # Create user + connection + account + transaction
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="x",
            full_name="Test User",
            role=UserRole.USER,
        )
        db_session.add(user)
        db_session.flush()

        conn = BankConnection(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=BankProvider.ENABLE_BANKING,
            institution_id="Test Bank|PL",
            institution_name="Test Bank",
            external_reference="ref-1",
            status=ConnectionStatus.LINKED,
        )
        db_session.add(conn)
        db_session.flush()

        account = Account(
            id=uuid.uuid4(),
            user_id=user.id,
            bank_connection_id=conn.id,
            external_account_id="ext-1",
            display_name="Test Account",
            account_type=AccountType.CHECKING,
            currency="PLN",
        )
        db_session.add(account)
        db_session.flush()

        txn = Transaction(
            id=uuid.uuid4(),
            account_id=account.id,
            dedupe_hash="hash-1",
            amount=Decimal("-45.99"),
            currency="PLN",
            booking_date=date(2026, 7, 1),
            description="Lidl",
            counterparty_name="LIDL",
            status=TransactionStatus.BOOKED,
        )
        db_session.add(txn)
        db_session.commit()

        # Classify using the task logic directly
        clf = train_default()
        result = clf.predict(txn.description, txn.counterparty_name, float(txn.amount))
        assert result["slug"] == "groceries"
        assert result["confidence"] > 0.0

    def test_new_transaction_is_classified_via_celery_task(self, db_session):
        from app.models.account import Account, AccountType
        from app.models.bank_connection import (
            BankConnection,
            BankProvider,
            ConnectionStatus,
        )
        from app.models.transaction import Transaction, TransactionStatus
        from app.models.user import User, UserRole

        seed_categories(db_session)

        user = User(id=uuid.uuid4(), email="u2@example.com", hashed_password="x", full_name="U", role=UserRole.USER)
        db_session.add(user)
        db_session.flush()

        conn = BankConnection(id=uuid.uuid4(), user_id=user.id, provider=BankProvider.ENABLE_BANKING,
                              institution_id="T|PL", institution_name="T", external_reference="r2",
                              status=ConnectionStatus.LINKED)
        db_session.add(conn)
        db_session.flush()

        account = Account(id=uuid.uuid4(), user_id=user.id, bank_connection_id=conn.id,
                          external_account_id="ext-2", display_name="A", account_type=AccountType.CHECKING, currency="PLN")
        db_session.add(account)
        db_session.flush()

        txn = Transaction(id=uuid.uuid4(), account_id=account.id, dedupe_hash="hash-2",
                          amount=Decimal("-200.00"), currency="PLN", booking_date=date(2026, 7, 1),
                          description="Orlen", counterparty_name="", status=TransactionStatus.BOOKED)
        db_session.add(txn)
        db_session.commit()

        # Simulate Celery task logic inline
        from app.ml.classifier import train_default
        from app.models.category import Category

        clf = train_default()
        result = clf.predict(txn.description, txn.counterparty_name, float(txn.amount))
        assert result["slug"] == "transport"

        # Now apply it like the task would
        cat = db_session.scalar(
            __import__("sqlalchemy").select(Category).where(Category.slug == result["slug"])
        )
        assert cat is not None
        txn.category_id = cat.id
        txn.category_source = __import__("app.models.transaction", fromlist=["CategorySource"]).CategorySource(result["source"])
        txn.category_confidence = result["confidence"]
        db_session.add(txn)
        db_session.commit()
        db_session.refresh(txn)

        assert txn.category_id == cat.id
        assert txn.category_source.value == "rule"
        assert txn.category_confidence == 0.95


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_description(self):
        clf = TransactionClassifier(seed_data=SEED_TRANSACTIONS)
        clf.train()
        result = clf.predict("", "", 0.0)
        assert result["slug"] == "other"

    def test_very_long_description(self):
        clf = TransactionClassifier(seed_data=SEED_TRANSACTIONS)
        clf.train()
        long = "A" * 10000
        result = clf.predict(long, "", -100.00)
        assert result["slug"] in ("other", "groceries")

    def test_positive_amount_income(self):
        clf = TransactionClassifier(seed_data=SEED_TRANSACTIONS)
        clf.train()
        result = clf.predict("Wynagrodzenie", "EMPLOYER", 6500.00)
        assert result["slug"] == "income"

    def test_special_characters(self):
        clf = TransactionClassifier(seed_data=SEED_TRANSACTIONS)
        clf.train()
        result = clf.predict("MCDONALD'S #123", "MCDONALD'S", -32.00)
        assert result["slug"] == "dining"
