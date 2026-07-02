import uuid
from datetime import date
from decimal import Decimal

from app.services.transaction_service import compute_dedupe_hash

ACCOUNT_ID = uuid.uuid4()


def _hash(**overrides):
    kwargs = dict(
        account_id=ACCOUNT_ID,
        amount=Decimal("10.00"),
        currency="EUR",
        booking_date=date(2026, 6, 15),
        description="Coffee Shop",
    )
    kwargs.update(overrides)
    return compute_dedupe_hash(**kwargs)


class TestComputeDedupeHash:
    def test_is_deterministic(self):
        assert _hash() == _hash()

    def test_differs_across_accounts(self):
        assert _hash() != _hash(account_id=uuid.uuid4())

    def test_differs_on_amount(self):
        assert _hash() != _hash(amount=Decimal("10.01"))

    def test_differs_on_date(self):
        assert _hash() != _hash(booking_date=date(2026, 6, 16))

    def test_differs_on_description(self):
        assert _hash() != _hash(description="Bakery")

    def test_amount_representation_is_normalized(self):
        """Decimal("10") and Decimal("10.00") represent the same value
        and must hash identically even if a provider payload sends one
        shape one day and the other the next."""
        assert _hash(amount=Decimal("10")) == _hash(amount=Decimal("10.00"))

    def test_currency_case_is_normalized(self):
        assert _hash(currency="eur") == _hash(currency="EUR")

    def test_description_whitespace_and_case_are_normalized(self):
        assert _hash(description="  Coffee Shop  ") == _hash(description="coffee shop")
